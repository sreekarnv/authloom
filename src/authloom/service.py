import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import email_normalize
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import HTTPException, Request, status
from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import undefer

from authloom.db.schema import ResetPasswordToken, Session, User
from authloom.db.utils.time import utc_now
from authloom.dtos import (
    SessionResDto,
    SigninSrvInputDto,
    SignupSrvInputDto,
    UserResDto,
)
from authloom.exceptions import (
    InvalidCredentialsException,
    InvalidPasswordResetTokenException,
    PasswordPolicyCode,
    PasswordPolicyException,
    SessionCreationException,
    UserAlreadyExistsException,
)
from authloom.settings import AuthLoomConfig


def hash_session_token(token_raw: str) -> str:
    return hashlib.sha256(token_raw.encode("utf-8")).hexdigest()


def generate_session_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_session_token(token)


def hash_password_reset_token(token_raw: str) -> str:
    return hashlib.sha256(token_raw.encode("utf-8")).hexdigest()


def generate_password_reset_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_password_reset_token(token)


class AuthLoom:
    def __init__(self, config: AuthLoomConfig) -> None:
        self.config = config
        self.password_hasher = PasswordHasher()
        self.dummy_password_hash = self.password_hasher.hash(secrets.token_urlsafe(32))
        self.session_factory = config.session_factory

    def _validate_password_policy(self, password: str) -> None:
        if len(password) < self.config.password_config.min_length:
            raise PasswordPolicyException(
                code=PasswordPolicyCode.TOO_SHORT,
                message=(
                    f"Password must contains at least "
                    f"{self.config.password_config.min_length} characters."
                ),
            )

        if len(password) > self.config.password_config.max_length:
            raise PasswordPolicyException(
                code=PasswordPolicyCode.TOO_LONG,
                message=(
                    f"Password must contains at most "
                    f"{self.config.password_config.max_length} characters."
                ),
            )

    async def require_current_user(self, request: Request) -> User:
        token_raw = request.cookies.get(self.config.cookie_session.cookie_name)
        if not token_raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="you are not logged in",
            )

        user = await self.get_current_user(token_raw=token_raw)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="you are not logged in",
            )

        return user

    async def optional_current_user(self, request: Request) -> User | None:
        token_raw = request.cookies.get(self.config.cookie_session.cookie_name)
        if not token_raw:
            return None

        return await self.get_current_user(token_raw=token_raw)

    async def signup(
        self, input: SignupSrvInputDto
    ) -> tuple[UserResDto, SessionResDto]:
        self._validate_password_policy(input.password)
        email_normalizer = email_normalize.Normalizer()
        normalized_result = await email_normalizer.normalize(input.email)

        async with self.session_factory() as session:
            q = await session.execute(
                select(User)
                .where(User.email == normalized_result.normalized_address)
                .limit(1)
            )
            user = q.scalar_one_or_none()

            if user:
                raise UserAlreadyExistsException()

            hashed_password = self.password_hasher.hash(input.password)

            user = User(
                name=input.name,
                email=normalized_result.normalized_address,
                password=hashed_password,
            )

            session.add(user)
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                raise UserAlreadyExistsException() from None

            token_raw, token_hash = generate_session_token()
            auth_session = Session(
                token_hash=token_hash,
                user_id=user.id,
                expires_at=utc_now()
                + timedelta(seconds=self.config.cookie_session.ttl),
            )

            session.add(auth_session)

            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise SessionCreationException() from None

            await session.refresh(user)
            await session.refresh(auth_session)

            return UserResDto.model_validate(user), SessionResDto(
                id=auth_session.id,
                token_raw=token_raw,
                expires_at=auth_session.expires_at,
            )

    async def signin(
        self, input: SigninSrvInputDto
    ) -> tuple[UserResDto, SessionResDto]:
        if len(input.password) > self.config.password_config.max_length:
            raise InvalidCredentialsException()

        email_normalizer = email_normalize.Normalizer()
        normalized_result = await email_normalizer.normalize(input.email)

        async with self.session_factory() as session:
            q = await session.execute(
                select(User)
                .options(undefer(User.password))
                .where(User.email == normalized_result.normalized_address)
                .limit(1)
            )
            user = q.scalar_one_or_none()

            if user is None:
                try:
                    self.password_hasher.verify(
                        self.dummy_password_hash, input.password
                    )
                except VerificationError:
                    pass
                raise InvalidCredentialsException()

            try:
                self.password_hasher.verify(user.password, input.password)
            except (InvalidHashError, VerificationError):
                raise InvalidCredentialsException() from None

            token_raw, token_hash = generate_session_token()
            auth_session = Session(
                token_hash=token_hash,
                user_id=user.id,
                expires_at=utc_now()
                + timedelta(seconds=self.config.cookie_session.ttl),
            )
            session.add(auth_session)

            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise SessionCreationException() from None

            await session.refresh(auth_session)

            return UserResDto.model_validate(user), SessionResDto(
                id=auth_session.id,
                token_raw=token_raw,
                expires_at=auth_session.expires_at,
            )

    async def signout(self, token_raw: str) -> None:
        token_hash = hash_session_token(token_raw)

        async with self.session_factory() as session:
            q = await session.execute(
                select(Session).where(
                    Session.token_hash == token_hash,
                    Session.revoked_at.is_(None),
                    Session.expires_at > utc_now(),
                )
            )

            auth_session = q.scalar_one_or_none()

            if auth_session is None:
                return

            auth_session.revoked_at = utc_now()
            await session.commit()

    async def get_current_user(self, token_raw: str) -> User | None:
        token_hash = hash_session_token(token_raw)

        async with self.session_factory() as session:
            q = await session.execute(
                select(Session).where(
                    Session.token_hash == token_hash,
                    Session.revoked_at.is_(None),
                    Session.expires_at > utc_now(),
                )
            )
            auth_session = q.scalar_one_or_none()

            if auth_session is None:
                return None

            q = await session.execute(
                select(User).where(User.id == auth_session.user_id)
            )
            user = q.scalar_one_or_none()
            if user is None:
                return None

            return user

    async def delete_stale_sessions(self, *, before: datetime | None = None) -> int:
        cutoff = utc_now() if before is None else before

        if cutoff.tzinfo is None or cutoff.tzinfo.utcoffset(cutoff) is None:
            raise ValueError("before must be timezone-aware")

        cutoff = cutoff.astimezone(UTC)

        async with self.session_factory() as session:
            q = await session.execute(
                delete(Session).where(
                    or_(
                        Session.expires_at <= cutoff,
                        Session.revoked_at.is_not(None),
                    )
                )
            )
            await session.commit()

        return q.rowcount or 0

    async def revoke_all_sessions(
        self, *, user_id: str, except_session_id: str | None = None
    ) -> int:
        now = utc_now()
        conditions = [
            Session.user_id == user_id,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
        ]

        if except_session_id is not None:
            conditions.append(Session.id != except_session_id)

        async with self.session_factory() as session:
            q = await session.execute(
                update(Session).where(and_(*conditions)).values(revoked_at=now)
            )
            await session.commit()

        return q.rowcount or 0

    async def request_password_reset(self, email: str) -> str | None:
        email_normalizer = email_normalize.Normalizer()
        normalized_result = await email_normalizer.normalize(email)

        token = None

        async with self.session_factory() as session:
            userq = await session.execute(
                select(User)
                .where(User.email == normalized_result.normalized_address)
                .limit(1)
            )
            user = userq.scalar_one_or_none()

            if not user:
                return None

            token, token_hash = generate_password_reset_token()
            password_reset_token = ResetPasswordToken(
                token=token_hash,
                user_id=user.id,
                expires_at=utc_now() + timedelta(minutes=15),
            )
            session.add(password_reset_token)
            await session.commit()

        return token

    async def verify_token_reset_password(
        self, token_raw: str, new_password: str
    ) -> None:
        self._validate_password_policy(new_password)

        token_hash = hash_password_reset_token(token_raw=token_raw)
        now = utc_now()

        async with self.session_factory() as session:
            q = await session.execute(
                update(ResetPasswordToken)
                .where(
                    ResetPasswordToken.token == token_hash,
                    ResetPasswordToken.used_at.is_(None),
                    ResetPasswordToken.expires_at > now,
                )
                .values(used_at=now)
                .returning(ResetPasswordToken.user_id)
            )
            user_id = q.scalar_one_or_none()

            if user_id is None:
                raise InvalidPasswordResetTokenException()

            password_hash = self.password_hasher.hash(new_password)

            await session.execute(
                update(User).where(User.id == user_id).values(password=password_hash)
            )

            await session.commit()

    async def change_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        preserve_session_token_raw: str | None = None,
    ) -> UserResDto | None:
        self._validate_password_policy(new_password)

        async with self.session_factory() as session:
            select_query = await session.execute(
                select(User)
                .options(undefer(User.password))
                .where(User.id == user_id)
                .limit(1)
            )
            user = select_query.scalar_one_or_none()

            if not user:
                try:
                    self.password_hasher.verify(self.dummy_password_hash, new_password)
                except VerificationError:
                    pass
                raise InvalidCredentialsException() from None

            try:
                self.password_hasher.verify(user.password, current_password)
            except (InvalidHashError, VerificationError):
                raise InvalidCredentialsException() from None

            hashed_password = self.password_hasher.hash(new_password)
            update_query = await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(password=hashed_password)
                .returning(User)
            )
            user = update_query.scalar_one_or_none()

            conditions = [
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
                Session.expires_at > utc_now(),
            ]

            if preserve_session_token_raw is not None:
                conditions.append(
                    Session.token_hash != hash_session_token(preserve_session_token_raw)
                )

            await session.execute(
                update(Session).where(and_(*conditions)).values(revoked_at=utc_now())
            )
            await session.commit()

        return None if not user else UserResDto.model_validate(user)

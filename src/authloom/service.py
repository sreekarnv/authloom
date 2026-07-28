import hashlib
import secrets
from datetime import timedelta

import email_normalize
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import undefer

from authloom.db.schema import Session, User
from authloom.db.utils.time import utc_now
from authloom.dtos import (
    SessionResDto,
    SigninSrvInputDto,
    SignupSrvInputDto,
    UserResDto,
)
from authloom.exceptions import (
    InvalidCredentialsException,
    PasswordPolicyCode,
    PasswordPolicyException,
    SessionCreationException,
    UserAlreadyExistsException,
)
from authloom.settings import AuthLoomConfig


class AuthLoom:
    def __init__(self, config: AuthLoomConfig) -> None:
        self.config = config
        self.email_normalizer = email_normalize.Normalizer()
        self.password_hasher = PasswordHasher()
        self.session_factory = config.session_factory

    def __hash_session_token(self, token_raw: str) -> str:
        return hashlib.sha256(token_raw.encode("utf-8")).hexdigest()

    def __generate_session_token(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        return token, self.__hash_session_token(token)

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

    async def signup(
        self, input: SignupSrvInputDto
    ) -> tuple[UserResDto, SessionResDto]:
        if len(input.password) < self.config.password_config.min_length:
            raise PasswordPolicyException(
                code=PasswordPolicyCode.TOO_SHORT,
                message=(
                    f"Password must contains at least "
                    f"{self.config.password_config.min_length} characters."
                ),
            )

        if len(input.password) > self.config.password_config.max_length:
            raise PasswordPolicyException(
                code=PasswordPolicyCode.TOO_LONG,
                message=(
                    f"Password must contains at most "
                    f"{self.config.password_config.max_length} characters."
                ),
            )

        normalized_result = await self.email_normalizer.normalize(input.email)

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

            token_raw, token_hash = self.__generate_session_token()
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

        normalized_result = await self.email_normalizer.normalize(input.email)

        async with self.session_factory() as session:
            q = await session.execute(
                select(User)
                .options(undefer(User.password))
                .where(User.email == normalized_result.normalized_address)
                .limit(1)
            )
            user = q.scalar_one_or_none()

            if user is None:
                raise InvalidCredentialsException()

            try:
                self.password_hasher.verify(user.password, input.password)
            except VerifyMismatchError:
                raise InvalidCredentialsException() from None

            token_raw, token_hash = self.__generate_session_token()
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
        token_hash = self.__hash_session_token(token_raw)

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
        token_hash = self.__hash_session_token(token_raw)

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

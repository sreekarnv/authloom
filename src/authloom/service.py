import hashlib
import secrets
from datetime import timedelta

import email_normalize
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import undefer

from authloom.dtos import (
    SessionResDto,
    SigninSrvInputDto,
    SignupSrvInputDto,
    UserResDto,
)
from authloom.exceptions import InvalidCredentialsException, UserAlreadyExistsException
from authloom.schema import Session, User
from authloom.utils.time import utc_now


class AuthLoom:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.email_normalizer = email_normalize.Normalizer()
        self.password_hasher = PasswordHasher()

    async def __generate_session_token(self) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

        return token, token_hash

    async def signup(
        self, input: SignupSrvInputDto
    ) -> tuple[UserResDto, SessionResDto]:
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
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise UserAlreadyExistsException() from None

            await session.refresh(user)

            token_raw, token_hash = await self.__generate_session_token()
            auth_session = Session(
                token_hash=token_hash,
                user_id=user.id,
                expires_at=utc_now() + timedelta(days=7),
            )
            session.add(auth_session)

            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError() from None

            await session.refresh(auth_session)

            return UserResDto.model_validate(user), SessionResDto(
                id=auth_session.id,
                token_raw=token_raw,
                expires_at=auth_session.expires_at,
            )

    async def signin(self, input: SigninSrvInputDto) -> UserResDto:
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

            return UserResDto.model_validate(user)

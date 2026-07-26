import email_normalize
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import undefer

from authloom.dtos import SigninSrvInputDto, SignupSrvInputDto, UserResDto
from authloom.exceptions import InvalidCredentialsException, UserAlreadyExistsException
from authloom.schema import User


class AuthLoom:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory
        self.email_normalizer = email_normalize.Normalizer()
        self.password_hasher = PasswordHasher()

    async def signup(self, input: SignupSrvInputDto) -> UserResDto:
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

            return UserResDto.model_validate(user)

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

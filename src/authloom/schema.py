from cuid2 import cuid_wrapper
from sqlalchemy import DATETIME, VARCHAR, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

CUID_GENERATOR = cuid_wrapper()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "authloom_users"

    id = mapped_column(VARCHAR, primary_key=True, default=CUID_GENERATOR)
    name = mapped_column(VARCHAR, index=True)
    email = mapped_column(VARCHAR, unique=True, index=True)
    password = mapped_column(VARCHAR, deferred=True)
    created_at = mapped_column(
        DATETIME(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = mapped_column(
        DATETIME(timezone=True), server_default=func.now(), onupdate=func.now()
    )

from cuid2 import cuid_wrapper
from datetime import datetime

from sqlalchemy import DATETIME, VARCHAR, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship

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

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "authloom_sessions"

    id = mapped_column(VARCHAR, primary_key=True, default=CUID_GENERATOR)
    token_hash = mapped_column(VARCHAR(64), unique=True, index=True)
    expires_at = mapped_column(DATETIME(timezone=True))
    revoked_at = mapped_column(DATETIME(timezone=True), nullable=True)
    created_at = mapped_column(
        DATETIME(timezone=True), nullable=False, server_default=func.now()
    )

    user_id = mapped_column(
        ForeignKey(f"authloom_users.id", ondelete="CASCADE"), index=True
    )
    user: Mapped["User"] = relationship(back_populates="sessions")

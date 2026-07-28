from cuid2 import cuid_wrapper
from sqlalchemy import VARCHAR, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from authloom.db.utils.time import UTCDateTime, utc_now

CUID_GENERATOR = cuid_wrapper()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "authloom_users"

    id = mapped_column(VARCHAR, primary_key=True, default=CUID_GENERATOR)
    name = mapped_column(VARCHAR, index=True, nullable=False)
    email = mapped_column(VARCHAR, unique=True, index=True, nullable=False)
    password = mapped_column(VARCHAR, deferred=True, nullable=False)
    created_at = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )
    updated_at = mapped_column(
        UTCDateTime(), default=utc_now, server_default=func.now(), onupdate=utc_now
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    __tablename__ = "authloom_sessions"

    id = mapped_column(VARCHAR, primary_key=True, default=CUID_GENERATOR)
    token_hash = mapped_column(VARCHAR(64), unique=True, index=True, nullable=False)
    expires_at = mapped_column(UTCDateTime(), nullable=False)
    revoked_at = mapped_column(UTCDateTime(), nullable=True)
    created_at = mapped_column(
        UTCDateTime(), nullable=False, default=utc_now, server_default=func.now()
    )

    user_id = mapped_column(
        ForeignKey("authloom_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="sessions")

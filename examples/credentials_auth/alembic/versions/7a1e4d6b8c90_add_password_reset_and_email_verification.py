"""add password reset and email verification tables

Revision ID: 7a1e4d6b8c90
Revises: 2f77297b2da0
Create Date: 2026-08-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from authloom.db import UTCDateTime

revision: str = "7a1e4d6b8c90"
down_revision: str | Sequence[str] | None = "2f77297b2da0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "authloom_users",
        sa.Column(
            "email_verified_at", UTCDateTime(), nullable=True
        ),
    )

    op.create_table(
        "authloom_reset_password_tokens",
        sa.Column("id", sa.VARCHAR(), nullable=False),
        sa.Column("token", sa.VARCHAR(length=64), nullable=False),
        sa.Column("user_id", sa.VARCHAR(), nullable=False),
        sa.Column(
            "created_at",
            UTCDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", UTCDateTime(), nullable=False),
        sa.Column("used_at", UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["authloom_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_authloom_reset_password_tokens_token"),
        "authloom_reset_password_tokens",
        ["token"],
        unique=True,
    )
    op.create_index(
        op.f("ix_authloom_reset_password_tokens_user_id"),
        "authloom_reset_password_tokens",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "authloom_email_verification_tokens",
        sa.Column("id", sa.VARCHAR(), nullable=False),
        sa.Column("token_hash", sa.VARCHAR(length=64), nullable=False),
        sa.Column("user_id", sa.VARCHAR(), nullable=False),
        sa.Column(
            "created_at",
            UTCDateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", UTCDateTime(), nullable=False),
        sa.Column("used_at", UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["authloom_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_authloom_email_verification_tokens_token_hash"),
        "authloom_email_verification_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_authloom_email_verification_tokens_user_id"),
        "authloom_email_verification_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_authloom_email_verification_tokens_user_id"),
        table_name="authloom_email_verification_tokens",
    )
    op.drop_index(
        op.f("ix_authloom_email_verification_tokens_token_hash"),
        table_name="authloom_email_verification_tokens",
    )
    op.drop_table("authloom_email_verification_tokens")
    op.drop_index(
        op.f("ix_authloom_reset_password_tokens_user_id"),
        table_name="authloom_reset_password_tokens",
    )
    op.drop_index(
        op.f("ix_authloom_reset_password_tokens_token"),
        table_name="authloom_reset_password_tokens",
    )
    op.drop_table("authloom_reset_password_tokens")
    op.drop_column("authloom_users", "email_verified_at")

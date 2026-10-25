"""Add structured diary fields and durable daily summary claims.

Revision ID: 20261025_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

from app.database import Base
from app import models  # noqa: F401 - register metadata for fresh databases.

revision = "20261025_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    # Creates absent tables on a fresh database, while leaving existing tables/data intact.
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "auth_provider" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "auth_provider",
                sa.String(length=16),
                nullable=False,
                server_default="password",
            ),
        )

    existing = {column["name"] for column in inspector.get_columns("diary_entries")}
    additions = (
        ("title", sa.Column("title", sa.String(length=160), nullable=True)),
        ("mood", sa.Column("mood", sa.String(length=16), nullable=True)),
        (
            "entry_type",
            sa.Column(
                "entry_type",
                sa.String(length=24),
                nullable=False,
                server_default="user",
            ),
        ),
        ("summary_day", sa.Column("summary_day", sa.Date(), nullable=True)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(), nullable=True)),
    )
    for name, column in additions:
        if name not in existing:
            op.add_column("diary_entries", column)

    op.execute(
        sa.text(
            "UPDATE diary_entries SET updated_at = created_at "
            "WHERE updated_at IS NULL"
        )
    )


def downgrade():
    raise RuntimeError(
        "This data-preserving migration is forward-only. Restore a verified backup "
        "to roll back; dropping title, mood, or updated_at can destroy user data."
    )

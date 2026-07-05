"""add webhook_retry_count and webhook_last_error to payments

Revision ID: 002
Revises: 001
Create Date: 2026-07-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("webhook_retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "payments",
        sa.Column("webhook_last_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payments", "webhook_last_error")
    op.drop_column("payments", "webhook_retry_count")

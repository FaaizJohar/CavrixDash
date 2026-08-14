"""add provider sync backoff columns

Revision ID: b9f2a4c1e6d7
Revises: a8f3b1c2d4e5
Create Date: 2026-08-13 09:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b9f2a4c1e6d7'
down_revision: Union[str, None] = 'a8f3b1c2d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("providers", sa.Column("last_attempt_at", sa.String(40), nullable=False, server_default=""))
    op.add_column("providers", sa.Column("sync_error_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("providers", "sync_error_count")
    op.drop_column("providers", "last_attempt_at")
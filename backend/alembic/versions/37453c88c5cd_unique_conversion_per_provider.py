"""unique conversion per provider

Revision ID: 37453c88c5cd
Revises: 04713c9ef6a6
Create Date: 2026-08-13 02:58:06.222741

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '37453c88c5cd'
down_revision: Union[str, None] = '04713c9ef6a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A unique index (not a table constraint) so the replay guard is actually
    # created on SQLite, where ALTER TABLE ... ADD CONSTRAINT is unsupported.
    op.create_index(
        'uq_conversions_provider_conversion',
        'conversions',
        ['provider_id', 'conversion_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_conversions_provider_conversion', table_name='conversions')

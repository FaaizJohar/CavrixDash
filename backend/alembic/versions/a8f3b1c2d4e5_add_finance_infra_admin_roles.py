"""add finance_admin and infra_admin roles

Revision ID: a8f3b1c2d4e5
Revises: 37453c88c5cd
Create Date: 2026-08-13 07:00:00.000000

"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'a8f3b1c2d4e5'
down_revision: Union[str, None] = '37453c88c5cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_role(bind, name: str) -> None:
    exists = bind.execute(
        text("SELECT 1 FROM roles WHERE name = :name"), {"name": name}
    ).first()
    if not exists:
        now = datetime.now(timezone.utc).isoformat()
        bind.execute(
            text(
                "INSERT INTO roles (id, name, description, is_system, created_at, updated_at) "
                "VALUES (:id, :name, :description, true, :now, :now)"
            ),
            {
                "id": str(uuid4()),
                "name": name,
                "description": f"{name} role",
                "now": now,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    _ensure_role(bind, "finance_admin")
    _ensure_role(bind, "infra_admin")


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        text("DELETE FROM roles WHERE name IN ('finance_admin', 'infra_admin')")
    )

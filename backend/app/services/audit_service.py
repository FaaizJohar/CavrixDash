from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_audit(
    db: Session,
    *,
    actor_id: str,
    actor_name: str,
    action: str,
    category: str = "general",
    target_type: str = "",
    target_id: str = "",
    old_value: Any = None,
    new_value: Any = None,
    ip: str = "",
    user_agent: str = "",
    result: str = "success",
    meta: dict[str, Any] | None = None,
) -> None:
    def ser(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, default=str, ensure_ascii=False)[:4000]
        return str(v)[:4000]

    entry = AuditLog(
        actor_id=actor_id,
        actor_name=actor_name[:120],
        action=action[:200],
        category=category,
        target_type=target_type,
        target_id=target_id,
        old_value=ser(old_value),
        new_value=ser(new_value),
        ip=ip or "",
        user_agent=user_agent[:400] if user_agent else "",
        result=result,
        meta=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(entry)
    db.commit()

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class SystemSetting(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="")
    section: Mapped[str] = mapped_column(String(40), default="general", index=True)
    kind: Mapped[str] = mapped_column(String(20), default="string")  # string|number|bool|json
    label: Mapped[str] = mapped_column(String(200), default="")
    public: Mapped[bool] = mapped_column(String(5), default="false")
    updated_by: Mapped[str] = mapped_column(String(36), default="")


class SystemConfig(Base, TimestampMixin, UUIDPrimaryKeyMixin):
    """Typed global config store (singleton row for composite platform config)."""

    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, default="{}")  # JSON

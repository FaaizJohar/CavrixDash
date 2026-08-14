from __future__ import annotations

from app.providers.ad_gem import AdGemAdapter
from app.providers.base import ProviderAdapter
from app.providers.cpa_lead import CPAleadAdapter
from app.providers.google_ad_manager import GoogleAdManagerAdapter
from app.providers.mock import MockProviderAdapter
from app.providers.shrink_me import ShrinkMeAdapter

_REGISTRY: dict[str, ProviderAdapter] = {
    adapter.code: adapter()
    for adapter in [
        CPAleadAdapter,
        AdGemAdapter,
        GoogleAdManagerAdapter,
        ShrinkMeAdapter,
        MockProviderAdapter,
    ]
}


def get_adapter(code: str) -> ProviderAdapter | None:
    return _REGISTRY.get(code)


def list_adapters() -> list[dict]:
    return [
        {
            "code": a.code,
            "name": a.name,
            "kind": a.kind,
        }
        for a in _REGISTRY.values()
    ]

"""Base interfaces and plugin registry for recall data sources."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, Any, Callable


class RawFetcher(ABC):
    @abstractmethod
    def fetch(self, since: str, until: str) -> Iterable[Dict[str, Any]]:  # dates ISO YYYY-MM-DD
        ...


class Normalizer(ABC):
    @abstractmethod
    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        ...


class DataSourcePlugin(ABC):
    id: str  # unique id e.g. 'us_fda_enforcement'
    country: str  # ISO2
    agency: str
    supports_incremental: bool = True
    incremental_field: str | None = None  # underlying source field used for date filtering

    @abstractmethod
    def fetch_raw(self, since: str, until: str):
        ...

    @abstractmethod
    def normalize_batch(self, raws: Iterable[Dict[str, Any]]):
        ...


PLUGIN_REGISTRY: Dict[str, DataSourcePlugin] = {}


def register(plugin_cls: Callable[[], DataSourcePlugin] | type):  # decorator
    instance = plugin_cls() if isinstance(plugin_cls, type) else plugin_cls
    if instance.id in PLUGIN_REGISTRY:
        raise ValueError(f"Plugin id already registered: {instance.id}")
    PLUGIN_REGISTRY[instance.id] = instance
    return plugin_cls


def get_plugin(plugin_id: str) -> DataSourcePlugin:
    if plugin_id not in PLUGIN_REGISTRY:
        raise KeyError(f"Plugin '{plugin_id}' not found. Registered: {list(PLUGIN_REGISTRY)}")
    return PLUGIN_REGISTRY[plugin_id]
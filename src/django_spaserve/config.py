"""Configuration objects and frontend-path helpers.

The path helpers are faithful ports of FastAPI's ``_normalize_frontend_path``,
``_join_frontend_paths`` and ``_frontend_path_specificity`` so that multi-mount
ordering behaves identically.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Literal, Optional, Union

# A frontend ``Accept`` body transform: (raw_html_bytes, request) -> new_bytes.
HtmlTransform = Callable[[bytes, "object"], bytes]

Fallback = Optional[Literal["auto", "index.html", "404.html"]]

_VALID_FALLBACKS = {"auto", "index.html", "404.html", None}


def normalize_frontend_path(path: str) -> str:
    """Port of FastAPI ``_normalize_frontend_path``.

    A mount prefix must start with ``/``; every prefix except the root has its
    trailing slash stripped so ``/app`` and ``/app/`` are equivalent.
    """
    if not path:
        raise ValueError("A frontend path cannot be empty")
    if not path.startswith("/"):
        raise ValueError("A frontend path must start with '/'")
    if path != "/":
        path = path.rstrip("/")
    return path


def join_frontend_paths(prefix: str, path: str) -> str:
    """Port of FastAPI ``_join_frontend_paths``."""
    if not prefix:
        return path
    if path == "/":
        return prefix
    return prefix + path


def frontend_path_specificity(path: str) -> int:
    """Port of FastAPI ``_frontend_path_specificity``.

    Root is the least specific (``0``); otherwise longer prefixes win.
    """
    if path == "/":
        return 0
    return len(path)


def resolved_absolute_path(path: Union[str, os.PathLike]) -> str:
    """Port of FastAPI ``_get_resolved_absolute_path`` — for error messages."""
    return os.path.realpath(os.fspath(path))


@dataclass
class SpaConfig:
    """Declarative configuration for a single SPA mount.

    The dataclass performs no filesystem IO; existence is validated lazily by
    :mod:`django_spaserve.checks` (and eagerly by :func:`django_spaserve.spa_urls` when
    ``check_dir`` is true).
    """

    directory: Path
    prefix: str = "/"
    fallback: Fallback = "auto"
    check_dir: bool = True
    # SPA shells must never be cached or users get stale apps after a deploy.
    index_cache_control: str = "no-cache"
    # ``None`` leaves caching of hashed assets to the upstream server / WhiteNoise.
    asset_cache_control: Optional[str] = None
    # Off by default; opt-in hook for CSP-nonce / runtime-env injection into the shell.
    html_transform: Optional[HtmlTransform] = None

    def __post_init__(self) -> None:
        if self.fallback not in _VALID_FALLBACKS:
            raise ValueError(
                "fallback must be 'auto', 'index.html', '404.html', or None"
            )
        self.prefix = normalize_frontend_path(self.prefix)
        # Coerce to Path but do not resolve/stat — keep this object IO-free.
        self.directory = Path(self.directory)

    @property
    def specificity(self) -> int:
        return frontend_path_specificity(self.prefix)

    @classmethod
    def coerce(cls, value: Union["SpaConfig", dict]) -> "SpaConfig":
        """Accept an existing config or a plain settings dict."""
        if isinstance(value, SpaConfig):
            return value
        if isinstance(value, dict):
            return cls(**value)
        raise TypeError(f"Expected SpaConfig or dict, got {type(value).__name__!r}")


# --- registry --------------------------------------------------------------
# spa_urls() registers its configs here so `manage.py check` can validate
# Strategy A mounts too (not just settings.DJANGO_SPASERVE / Strategy B).
_REGISTERED_CONFIGS: List[SpaConfig] = []


def register_config(config: SpaConfig) -> None:
    _REGISTERED_CONFIGS.append(config)


def iter_registered_configs() -> List[SpaConfig]:
    return list(_REGISTERED_CONFIGS)

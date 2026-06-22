"""Strategy A — catch-all ``re_path`` URL patterns.

``spa_urls()`` returns URL patterns you place **last** in your root ``urlpatterns``
so the SPA never shadows a real backend route. Multiple mounts are emitted
longest-prefix-first so a ``/admin-spa`` mount is tried before a ``/`` mount.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Union

from django.urls import re_path
from django.urls.resolvers import URLPattern

from .checks import validate_config
from .config import SpaConfig, register_config
from .views import make_spa_view

__all__ = ["spa_urls", "spa_urls_multi"]


def _pattern_for(config: SpaConfig) -> URLPattern:
    """Build the anchored regex pattern for one mount."""
    if config.prefix == "/":
        regex = r"^(?P<path>.*)$"
    else:
        # "/app" -> match "app" (the mount root) and "app/<path>".
        literal = re.escape(config.prefix.lstrip("/"))
        regex = rf"^{literal}(?:/(?P<path>.*))?$"
    return re_path(regex, make_spa_view(config))


def _build(configs: Iterable[SpaConfig]) -> List[URLPattern]:
    ordered = sorted(configs, key=lambda c: c.specificity, reverse=True)
    patterns: List[URLPattern] = []
    for config in ordered:
        if config.check_dir:
            errors = validate_config(config)
            if errors:
                from django.core.exceptions import ImproperlyConfigured

                raise ImproperlyConfigured("; ".join(errors))
        register_config(config)
        patterns.append(_pattern_for(config))
    return patterns


def spa_urls(
    prefix: str = "/",
    *,
    directory,
    fallback="auto",
    check_dir: bool = True,
    **config_kwargs,
) -> List[URLPattern]:
    """Return catch-all URL patterns serving the SPA at ``prefix``.

    Place the result **last** in your root ``urlpatterns``::

        urlpatterns = [
            path("api/", include("myapi.urls")),
            *spa_urls("/", directory=BASE_DIR / "frontend/dist"),
        ]

    Extra keyword arguments (``index_cache_control``, ``asset_cache_control``,
    ``html_transform``) are forwarded to :class:`~django_spaserve.SpaConfig`.
    """
    config = SpaConfig(
        directory=directory,
        prefix=prefix,
        fallback=fallback,
        check_dir=check_dir,
        **config_kwargs,
    )
    return _build([config])


def spa_urls_multi(
    configs: Iterable[Union[SpaConfig, dict]],
) -> List[URLPattern]:
    """Return patterns for several mounts, ordered longest-prefix-first."""
    return _build([SpaConfig.coerce(c) for c in configs])

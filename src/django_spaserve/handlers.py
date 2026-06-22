"""Strategy B — ``handler404`` fallback.

Django invokes ``handler404`` only after *every* URL pattern has failed to match,
which gives us FastAPI's low-priority semantics for free: this can never shadow a
real route. Pair it with WhiteNoise/CDN serving the real asset files; this handler
then only decides shell-vs-404 for the requests that fell through.
"""

from __future__ import annotations

from typing import List, Optional

from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.defaults import page_not_found

from .config import SpaConfig
from .views import decide_response

__all__ = ["handler404", "load_settings_configs"]


def load_settings_configs() -> List[SpaConfig]:
    """Read ``settings.DJANGO_SPASERVE`` (a list of dicts/SpaConfig) into configs."""
    raw = getattr(settings, "DJANGO_SPASERVE", None) or []
    return [SpaConfig.coerce(item) for item in raw]


def _match_prefix(prefix: str, path_info: str) -> Optional[str]:
    """Return the sub-path for ``path_info`` under ``prefix``, or ``None``.

    Port of FastAPI ``_FrontendRoute._get_frontend_path`` against an absolute
    ``request.path_info`` (which always starts with ``/``).
    """
    if prefix == "/":
        return path_info.lstrip("/")
    if path_info == prefix:
        return ""
    nested = prefix + "/"
    if path_info.startswith(nested):
        return path_info[len(nested) :]
    return None


def handler404(request, exception=None) -> HttpResponse:
    """Project-level ``handler404`` that falls back to the SPA shell.

    Wire it up with ``handler404 = "django_spaserve.handler404"`` in your root
    ``urls.py`` and configure mounts via ``settings.DJANGO_SPASERVE``.
    """
    configs = sorted(load_settings_configs(), key=lambda c: c.specificity, reverse=True)
    for config in configs:
        sub_path = _match_prefix(config.prefix, request.path_info)
        if sub_path is None:
            continue
        try:
            return decide_response(request, sub_path, config)
        except Http404:
            # This mount declined; let a more general mount (or Django) handle it.
            continue
    return page_not_found(request, exception or Http404())

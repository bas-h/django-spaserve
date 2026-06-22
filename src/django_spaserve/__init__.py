"""django-spaserve — serve a built SPA from Django with correct routing fallback.

Public API::

    from django_spaserve import spa_urls, spa_urls_multi   # Strategy A (catch-all)
    from django_spaserve import handler404                  # Strategy B (handler404)
    from django_spaserve import SpaConfig, decide_response, is_navigation_request
"""

from __future__ import annotations

from .config import SpaConfig
from .handlers import handler404
from .navigation import is_navigation_request, iter_accept_media_types
from .urls import spa_urls, spa_urls_multi
from .views import decide_response, make_spa_view, serve_spa

default_app_config = "django_spaserve.apps.DjangoSpaConfig"

__version__ = "0.1.0"

__all__ = [
    "SpaConfig",
    "spa_urls",
    "spa_urls_multi",
    "serve_spa",
    "make_spa_view",
    "decide_response",
    "handler404",
    "is_navigation_request",
    "iter_accept_media_types",
    "__version__",
]

"""The shared decision core (``decide_response``) and the Strategy A view.

``decide_response`` ports FastAPI ``_FrontendStaticFiles.get_response`` — the
three-way decision between *real file*, *client-side route -> shell*, and
*genuine 404*. Both Strategy A (catch-all ``re_path``) and Strategy B
(``handler404``) call it so behavior is identical.
"""

from __future__ import annotations

import os
from typing import Optional

from django.http import (
    Http404,
    HttpResponse,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
)

from .config import SpaConfig
from .files import (
    file_response,
    is_directory,
    is_regular_file,
    lookup_path,
    normalize_subpath,
)
from .navigation import is_navigation_request

__all__ = ["decide_response", "make_spa_view", "serve_spa"]

_ALLOWED_METHODS = ("GET", "HEAD")


def _fallback_exists(config: SpaConfig, name: str) -> bool:
    _, stat_result = lookup_path(config.directory, name)
    return is_regular_file(stat_result)


def _serve(
    request,
    config: SpaConfig,
    full_path: str,
    stat_result: os.stat_result,
    *,
    status: int,
) -> HttpResponse:
    """Serve a resolved file, applying shell-specific cache + transform rules."""
    is_index = os.path.basename(full_path) == "index.html"
    cache_control = (
        config.index_cache_control if is_index else config.asset_cache_control
    )

    if is_index and config.html_transform is not None:
        # Dynamic shell: read, transform, and serve without conditional-GET/FileResponse.
        with open(full_path, "rb") as handle:
            content = config.html_transform(handle.read(), request)
        body = b"" if request.method == "HEAD" else content
        response = HttpResponse(body, content_type="text/html", status=status)
        response["Content-Length"] = str(len(content))
        if cache_control:
            response["Cache-Control"] = cache_control
        return response

    return file_response(
        request, full_path, stat_result, status=status, cache_control=cache_control
    )


def decide_response(request, sub_path: str, config: SpaConfig) -> HttpResponse:
    """Resolve one request against one SPA mount.

    Returns a ``405`` for non GET/HEAD, a file response for real files, a
    trailing-slash redirect for directories with an ``index.html``, the SPA
    shell (or ``404.html``) per the configured ``fallback``, or raises
    :class:`~django.http.Http404` for genuinely missing assets / non-navigations.
    """
    if request.method not in _ALLOWED_METHODS:
        return HttpResponseNotAllowed(_ALLOWED_METHODS)

    norm = normalize_subpath(sub_path or "")
    full_path, stat_result = lookup_path(config.directory, norm)

    if is_regular_file(stat_result):
        return _serve(request, config, full_path, stat_result, status=200)

    if is_directory(stat_result):
        index_rel = os.path.join(norm, "index.html")
        index_path, index_stat = lookup_path(config.directory, index_rel)
        if is_regular_file(index_stat):
            if not request.path.endswith("/"):
                location = request.path + "/"
                query = request.META.get("QUERY_STRING")
                if query:
                    location = f"{location}?{query}"
                return HttpResponseRedirect(location)
            return _serve(request, config, index_path, index_stat, status=200)

    # No real file matched -> decide between the shell, a 404.html, or a real 404.
    if config.fallback == "404.html" or (
        config.fallback == "auto" and _fallback_exists(config, "404.html")
    ):
        path_404, stat_404 = lookup_path(config.directory, "404.html")
        if is_regular_file(stat_404):
            return _serve(request, config, path_404, stat_404, status=404)

    if (
        config.fallback == "index.html"
        or (config.fallback == "auto" and _fallback_exists(config, "index.html"))
    ) and is_navigation_request(request):
        index_path, index_stat = lookup_path(config.directory, "index.html")
        if is_regular_file(index_stat):
            return _serve(request, config, index_path, index_stat, status=200)

    raise Http404("No SPA file or shell matched this request.")


def make_spa_view(config: SpaConfig):
    """Build a Django view bound to ``config`` (used by :func:`spa_urls`)."""

    def view(request, path: Optional[str] = ""):
        return decide_response(request, path or "", config)

    view.spa_config = config  # introspection / debugging aid
    return view


def serve_spa(request, path: str = "", *, config: SpaConfig) -> HttpResponse:
    """Functional entry point: ``decide_response`` with an explicit ``config``."""
    return decide_response(request, path, config)

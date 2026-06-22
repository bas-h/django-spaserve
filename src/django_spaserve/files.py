"""Safe static-file lookup and response construction.

``lookup_path`` mirrors Starlette ``StaticFiles.lookup_path`` with
``follow_symlink=False``: the candidate path is fully resolved with
``os.path.realpath`` and then checked to be contained within the resolved
directory, so both ``..`` traversal and symlinks escaping the root are rejected.
"""

from __future__ import annotations

import mimetypes
import os
import stat
from typing import Optional, Tuple

from django.http import (
    FileResponse,
    HttpResponse,
    HttpResponseNotModified,
)
from django.utils.http import http_date
from django.views.static import was_modified_since

__all__ = [
    "normalize_subpath",
    "lookup_path",
    "is_regular_file",
    "is_directory",
    "file_response",
]


def normalize_subpath(path: str) -> str:
    """Collapse a URL sub-path to a filesystem-relative path.

    Port of FastAPI ``_FrontendStaticFiles.get_path``. An empty path (the mount
    root) collapses to ``"."`` which ``lookup_path`` resolves to the directory
    itself. Any ``..`` segments are left intact here and rejected later by the
    containment check in :func:`lookup_path`.
    """
    return os.path.normpath(os.path.join(*path.split("/")))


def lookup_path(
    directory: os.PathLike, path: str
) -> Tuple[str, Optional[os.stat_result]]:
    """Resolve ``path`` inside ``directory``, refusing to escape the root.

    Returns ``(full_path, stat_result)``; ``stat_result`` is ``None`` when the
    path does not exist or would escape the directory.
    """
    joined = os.path.join(directory, path)
    # realpath resolves symlinks; an escaping symlink lands outside `directory`.
    full_path = os.path.realpath(joined)
    directory_real = os.path.realpath(directory)
    if os.path.commonpath([full_path, directory_real]) != directory_real:
        return "", None
    try:
        return full_path, os.stat(full_path)
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return "", None


def is_regular_file(stat_result: Optional[os.stat_result]) -> bool:
    return stat_result is not None and stat.S_ISREG(stat_result.st_mode)


def is_directory(stat_result: Optional[os.stat_result]) -> bool:
    return stat_result is not None and stat.S_ISDIR(stat_result.st_mode)


def _etag(stat_result: os.stat_result) -> str:
    return f'"{int(stat_result.st_mtime)}-{stat_result.st_size}"'


def file_response(
    request,
    full_path: str,
    stat_result: os.stat_result,
    *,
    status: int = 200,
    cache_control: Optional[str] = None,
) -> HttpResponse:
    """Build a response for a real file with caching/conditional-GET headers.

    Honors ``If-Modified-Since`` (returns ``304`` for unchanged ``200`` GET/HEAD),
    sets ``Last-Modified`` / ``ETag`` / ``Content-Length`` and, for HEAD, omits the
    body. ``cache_control`` is applied when provided (e.g. ``no-cache`` for shells).
    """
    last_modified = stat_result.st_mtime
    method = request.method if request is not None else "GET"

    def _decorate(response: HttpResponse) -> HttpResponse:
        response["Last-Modified"] = http_date(last_modified)
        response["ETag"] = _etag(stat_result)
        if cache_control:
            response["Cache-Control"] = cache_control
        return response

    if status == 200 and method in ("GET", "HEAD"):
        if not was_modified_since(
            request.headers.get("If-Modified-Since"), last_modified
        ):
            return _decorate(HttpResponseNotModified())

    content_type, encoding = mimetypes.guess_type(full_path)
    content_type = content_type or "application/octet-stream"

    if method == "HEAD":
        response: HttpResponse = HttpResponse(content_type=content_type, status=status)
    else:
        response = FileResponse(
            open(full_path, "rb"), content_type=content_type, status=status
        )
    response["Content-Length"] = str(stat_result.st_size)
    if encoding:
        response["Content-Encoding"] = encoding
    return _decorate(response)

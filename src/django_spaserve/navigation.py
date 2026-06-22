"""Navigation-vs-asset disambiguation — the crux of correct SPA fallback.

This is a near-verbatim port of FastAPI's ``_is_frontend_navigation_request`` and
``_iter_accept_media_types`` (``fastapi/routing.py``), adapted to Django's
``HttpRequest``.

The rule, in plain terms:

* A path whose final segment has a file extension (``app.js``, ``logo.png``) is
  *never* a navigation — it is an asset request, so we must not serve the shell.
* Otherwise we inspect the ``Accept`` header: a browser navigation asks for
  ``text/html`` (serve the shell); a ``fetch()`` asking for JSON does not (let it
  404); a bare ``*/*`` (curl, default fetch) is treated as a navigation.
"""

from __future__ import annotations

import email.message
import os
from typing import Iterator, Tuple

__all__ = ["iter_accept_media_types", "is_navigation_request"]


def iter_accept_media_types(accept: str) -> Iterator[Tuple[str, float]]:
    """Parse an ``Accept`` header into ``(media_type, quality)`` pairs.

    Port of FastAPI ``_iter_accept_media_types``. Uses ``email.message.Message``
    to parse ``;q=`` parameters exactly like FastAPI does, so ``text/html;q=0.9``
    yields ``("text/html", 0.9)``.
    """
    for raw_value in accept.split(","):
        message = email.message.Message()
        message["content-type"] = raw_value.strip()
        q = message.get_param("q")
        quality = 1.0
        if isinstance(q, str):
            try:
                quality = float(q)
            except ValueError:
                pass
        yield (
            f"{message.get_content_maintype()}/{message.get_content_subtype()}",
            quality,
        )


def is_navigation_request(request) -> bool:
    """Return ``True`` when the request should receive the SPA shell.

    Port of FastAPI ``_is_frontend_navigation_request``.
    """
    final_segment = request.path_info.rsplit("/", 1)[-1]
    if os.path.splitext(final_segment)[1]:
        # The path looks like a file (has an extension) -> it is an asset.
        return False

    wildcard_accepted = False
    html_rejected = False
    for media_type, quality in iter_accept_media_types(
        request.headers.get("Accept", "")
    ):
        if media_type in {"text/html", "application/xhtml+xml"}:
            if quality == 0:
                html_rejected = True
            else:
                return True
        elif media_type == "*/*" and quality != 0:
            wildcard_accepted = True
    return wildcard_accepted and not html_rejected

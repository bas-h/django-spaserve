"""The navigation heuristic — ported from FastAPI's test matrix."""

from __future__ import annotations

import pytest
from django.test import RequestFactory

from django_spaserve.navigation import is_navigation_request, iter_accept_media_types

rf = RequestFactory()


def _req(path="/dashboard", accept=None):
    headers = {}
    if accept is not None:
        headers["HTTP_ACCEPT"] = accept
    return rf.get(path, **headers)


@pytest.mark.parametrize(
    "accept,expected",
    [
        ("text/html", True),
        ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", True),
        ("application/xhtml+xml", True),
        ("text/html;q=0.9", True),
        ("*/*", True),
        ("text/html;q=0", False),  # HTML explicitly rejected
        ("application/json", False),
        ("application/json,text/plain", False),
        ("*/*;q=0", False),  # wildcard rejected
        ("text/html;q=0,*/*", False),  # html rejected wins even with wildcard
        ("", False),  # empty Accept -> not a navigation
    ],
)
def test_accept_header_decides_navigation(accept, expected):
    assert is_navigation_request(_req(accept=accept)) is expected


@pytest.mark.parametrize("ext_path", ["/assets/app.js", "/logo.png", "/x/style.css"])
def test_extension_paths_are_never_navigation(ext_path):
    # Even with a perfect browser Accept header, a path with an extension is an asset.
    assert is_navigation_request(_req(path=ext_path, accept="text/html")) is False


def test_dotless_final_segment_is_eligible():
    assert is_navigation_request(_req(path="/users/42", accept="text/html")) is True


def test_dotted_directory_but_dotless_final_segment():
    # The check only looks at the FINAL segment.
    assert (
        is_navigation_request(_req(path="/v1.2/settings", accept="text/html")) is True
    )


def test_iter_accept_media_types_parses_quality():
    pairs = list(iter_accept_media_types("text/html;q=0.9, application/json"))
    assert pairs == [("text/html", 0.9), ("application/json", 1.0)]


def test_iter_accept_media_types_bad_quality_defaults_to_one():
    pairs = list(iter_accept_media_types("text/html;q=bogus"))
    assert pairs == [("text/html", 1.0)]

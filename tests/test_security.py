"""Path traversal, symlink escape, and method restrictions."""

from __future__ import annotations

import os

import pytest
from django.http import Http404
from django.test import RequestFactory

from django_spaserve import SpaConfig, decide_response
from django_spaserve.files import lookup_path

rf = RequestFactory()


@pytest.mark.parametrize(
    "evil",
    [
        "../../etc/passwd",
        "../../../../../../etc/passwd",
        "..",
        "sub/../../secret",
    ],
)
def test_lookup_path_rejects_traversal(spa_dir, evil):
    full_path, stat_result = lookup_path(spa_dir, evil)
    assert stat_result is None
    assert full_path == ""


def test_symlink_escape_is_blocked(tmp_path, spa_dir):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")
    link = spa_dir / "leak"
    os.symlink(secret, link)

    full_path, stat_result = lookup_path(spa_dir, "leak")
    assert stat_result is None  # realpath escapes the root -> rejected


def test_traversal_request_never_leaks_file(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("TOP SECRET")
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>App</title>")
    config = SpaConfig(directory=dist, fallback=None)

    request = rf.get("/etc/passwd", HTTP_ACCEPT="text/html")
    with pytest.raises(Http404):
        decide_response(request, "../../secret.txt", config)


def test_non_get_head_methods_rejected(spa_dir):
    config = SpaConfig(directory=spa_dir, fallback="index.html")
    for method in ("post", "put", "delete", "patch"):
        request = getattr(rf, method)("/dashboard")
        resp = decide_response(request, "dashboard", config)
        assert resp.status_code == 405


def test_get_and_head_allowed(spa_dir):
    config = SpaConfig(directory=spa_dir, fallback="index.html")
    for method in ("get", "head"):
        request = getattr(rf, method)("/dashboard", HTTP_ACCEPT="text/html")
        resp = decide_response(request, "dashboard", config)
        assert resp.status_code == 200

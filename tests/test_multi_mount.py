"""Longest-prefix-wins across multiple SPA mounts."""

from __future__ import annotations

import pytest
from django.test import Client, override_settings

from django_spaserve import spa_urls_multi

BROWSER = {"HTTP_ACCEPT": "text/html"}


@pytest.fixture
def two_dists(tmp_path):
    root = tmp_path / "root"
    admin = tmp_path / "admin"
    for d, marker in ((root, "ROOT-APP"), (admin, "ADMIN-APP")):
        (d / "assets").mkdir(parents=True)
        (d / "index.html").write_text(f"<title>{marker}</title>")
        (d / "assets" / "app.js").write_text(f"// {marker}")
    return root, admin


def _client(make_urlconf, mounts):
    name = make_urlconf(spa_urls_multi(mounts))
    return name


@pytest.mark.parametrize("order", ["specific-first", "general-first"])
def test_longest_prefix_wins_regardless_of_order(make_urlconf, two_dists, order):
    root, admin = two_dists
    mounts = [
        {"prefix": "/admin-spa", "directory": admin, "fallback": "index.html"},
        {"prefix": "/", "directory": root, "fallback": "index.html"},
    ]
    if order == "general-first":
        mounts.reverse()

    name = _client(make_urlconf, mounts)
    with override_settings(ROOT_URLCONF=name):
        client = Client()
        admin_resp = client.get("/admin-spa/users", **BROWSER)
        root_resp = client.get("/dashboard", **BROWSER)
        admin_redirect = client.get("/admin-spa", **BROWSER)
        admin_root = client.get("/admin-spa/", **BROWSER)

    assert b"ADMIN-APP" in admin_resp.getvalue()
    assert b"ROOT-APP" in root_resp.getvalue()
    # The bare mount prefix is a directory -> redirect to add the trailing slash,
    # which then serves that mount's shell.
    assert admin_redirect.status_code == 302
    assert admin_redirect["Location"] == "/admin-spa/"
    assert b"ADMIN-APP" in admin_root.getvalue()


def test_each_mount_serves_its_own_assets(make_urlconf, two_dists):
    root, admin = two_dists
    mounts = [
        {"prefix": "/admin-spa", "directory": admin, "fallback": "index.html"},
        {"prefix": "/", "directory": root, "fallback": "index.html"},
    ]
    name = _client(make_urlconf, mounts)
    with override_settings(ROOT_URLCONF=name):
        client = Client()
        assert b"ADMIN-APP" in client.get("/admin-spa/assets/app.js").getvalue()
        assert b"ROOT-APP" in client.get("/assets/app.js").getvalue()

"""Cache-Control, conditional GET, and the html_transform hook."""

from __future__ import annotations

from django.test import Client, override_settings

from django_spaserve import spa_urls

BROWSER = {"HTTP_ACCEPT": "text/html"}


def test_shell_is_no_cache_by_default(make_urlconf, spa_dir):
    name = make_urlconf(spa_urls("/", directory=spa_dir, fallback="index.html"))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/", **BROWSER)
    assert resp["Cache-Control"] == "no-cache"


def test_asset_cache_control_applied(make_urlconf, spa_dir):
    name = make_urlconf(
        spa_urls(
            "/",
            directory=spa_dir,
            asset_cache_control="public, max-age=31536000, immutable",
        )
    )
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/assets/app.js")
    assert resp["Cache-Control"] == "public, max-age=31536000, immutable"


def test_conditional_get_returns_304(make_urlconf, spa_dir):
    name = make_urlconf(spa_urls("/", directory=spa_dir))
    with override_settings(ROOT_URLCONF=name):
        client = Client()
        first = client.get("/assets/app.js")
        last_modified = first["Last-Modified"]
        second = client.get("/assets/app.js", HTTP_IF_MODIFIED_SINCE=last_modified)
    assert first.status_code == 200
    assert second.status_code == 304


def test_etag_present(make_urlconf, spa_dir):
    name = make_urlconf(spa_urls("/", directory=spa_dir))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/assets/app.js")
    assert resp["ETag"]


def test_html_transform_hook(make_urlconf, spa_dir):
    def inject(html: bytes, request) -> bytes:
        return html.replace(b"App shell", b"Injected " + request.path.encode())

    name = make_urlconf(
        spa_urls("/", directory=spa_dir, fallback="index.html", html_transform=inject)
    )
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/dashboard", **BROWSER)
    assert resp.status_code == 200
    assert b"Injected /dashboard" in resp.getvalue()

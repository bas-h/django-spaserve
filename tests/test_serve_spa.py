"""Strategy A end-to-end through the Django test client."""

from __future__ import annotations

from django.test import Client, override_settings
from django.urls import path

from django_spaserve import spa_urls

BROWSER = {"HTTP_ACCEPT": "text/html"}


def _urls(make_urlconf, spa_dir, **kwargs):
    def ping(request):
        from django.http import HttpResponse

        return HttpResponse("pong")

    return make_urlconf(
        [path("api/ping", ping), *spa_urls("/", directory=spa_dir, **kwargs)]
    )


def test_real_file_served_with_content_type(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/assets/app.js")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith(
        ("text/javascript", "application/javascript")
    )
    assert b"console.log" in resp.getvalue()


def test_real_route_still_wins(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/api/ping")
    assert resp.status_code == 200
    assert resp.content == b"pong"


def test_unknown_route_browser_gets_shell(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/dashboard/settings", **BROWSER)
    assert resp.status_code == 200
    assert b"App shell" in resp.getvalue()


def test_unknown_js_asset_is_404_not_shell(make_urlconf, spa_dir):
    # The classic bug: a missing .js must NOT return index.html.
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/assets/typo.js", **BROWSER)
    assert resp.status_code == 404
    assert b"App shell" not in resp.getvalue()


def test_ssg_404_html_wins_over_shell_in_auto_mode(make_urlconf, make_dist):
    # When 404.html is present, `auto` serves it (with 404) for every miss,
    # even browser navigations -- the faithful FastAPI/SSG-export semantics.
    dist = make_dist(fallback_404=True)
    name = make_urlconf(spa_urls("/", directory=dist, fallback="auto"))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/dashboard", **BROWSER)
    assert resp.status_code == 404
    assert b"Not found" in resp.getvalue()


def test_root_serves_index(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/", **BROWSER)
    assert resp.status_code == 200
    assert b"App shell" in resp.getvalue()


def test_post_returns_405(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().post("/dashboard", **BROWSER)
    assert resp.status_code == 405
    assert set(resp["Allow"].replace(" ", "").split(",")) == {"GET", "HEAD"}


def test_directory_redirects_to_trailing_slash(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/sub", **BROWSER)
    assert resp.status_code == 302
    assert resp["Location"] == "/sub/"


def test_directory_with_slash_serves_its_index(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/sub/", **BROWSER)
    assert resp.status_code == 200
    assert b"Sub shell" in resp.getvalue()


def test_redirect_preserves_query_string(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/sub?a=1&b=2", **BROWSER)
    assert resp.status_code == 302
    assert resp["Location"] == "/sub/?a=1&b=2"


def test_head_request_has_no_body(make_urlconf, spa_dir):
    name = _urls(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name):
        resp = Client().head("/assets/app.js")
    assert resp.status_code == 200
    assert resp.getvalue() == b""
    assert int(resp["Content-Length"]) > 0


# --- fallback modes --------------------------------------------------------


def test_fallback_index_html_mode(make_urlconf, make_dist):
    dist = make_dist(fallback_404=False)  # only index.html
    name = make_urlconf(spa_urls("/", directory=dist, fallback="index.html"))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/anything", **BROWSER)
    assert resp.status_code == 200
    assert b"App shell" in resp.getvalue()


def test_fallback_404_html_mode_ignores_navigation(make_urlconf, make_dist):
    dist = make_dist(fallback_404=True)
    name = make_urlconf(spa_urls("/", directory=dist, fallback="404.html"))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/anything", **BROWSER)
    assert resp.status_code == 404
    assert b"Not found" in resp.getvalue()


def test_fallback_none_always_404s(make_urlconf, spa_dir):
    name = make_urlconf(spa_urls("/", directory=spa_dir, fallback=None))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/anything", **BROWSER)
    assert resp.status_code == 404
    # Real Django 404, not the SPA shell.
    assert b"App shell" not in resp.getvalue()


def test_auto_without_404_serves_shell(make_urlconf, make_dist):
    dist = make_dist(fallback_404=False)
    name = make_urlconf(spa_urls("/", directory=dist, fallback="auto"))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/dashboard", **BROWSER)
    assert resp.status_code == 200
    assert b"App shell" in resp.getvalue()


def test_non_navigation_json_request_404s_not_shell(make_urlconf, make_dist):
    dist = make_dist(fallback_404=False)
    name = make_urlconf(spa_urls("/", directory=dist, fallback="index.html"))
    with override_settings(ROOT_URLCONF=name):
        resp = Client().get("/api/thing", HTTP_ACCEPT="application/json")
    assert resp.status_code == 404
    assert b"App shell" not in resp.getvalue()

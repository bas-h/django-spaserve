"""Strategy B end-to-end: handler404 fallback."""

from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from django.test import Client, override_settings
from django.urls import path

from django_spaserve import handler404

BROWSER = {"HTTP_ACCEPT": "text/html"}


def _project(make_urlconf, spa_dir, fallback="index.html"):
    def ping(request):
        return HttpResponse("pong")

    def api_thing(request):
        return JsonResponse({"ok": True})

    name = make_urlconf(
        [path("api/ping", ping), path("api/thing", api_thing)],
        handler404=handler404,
    )
    return name, [{"prefix": "/", "directory": str(spa_dir), "fallback": fallback}]


def test_navigation_falls_back_to_shell(make_urlconf, spa_dir):
    name, cfg = _project(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name, DJANGO_SPASERVE=cfg):
        resp = Client().get("/dashboard", **BROWSER)
    assert resp.status_code == 200
    assert b"App shell" in resp.getvalue()


def test_real_route_unaffected(make_urlconf, spa_dir):
    name, cfg = _project(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name, DJANGO_SPASERVE=cfg):
        resp = Client().get("/api/ping")
    assert resp.status_code == 200
    assert resp.content == b"pong"


def test_api_404_stays_real_404_for_json_clients(make_urlconf, spa_dir):
    name, cfg = _project(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name, DJANGO_SPASERVE=cfg):
        resp = Client().get("/api/missing", HTTP_ACCEPT="application/json")
    assert resp.status_code == 404
    assert b"App shell" not in resp.getvalue()


def test_missing_asset_404s(make_urlconf, spa_dir):
    name, cfg = _project(make_urlconf, spa_dir)
    with override_settings(ROOT_URLCONF=name, DJANGO_SPASERVE=cfg):
        resp = Client().get("/assets/typo.js", **BROWSER)
    assert resp.status_code == 404
    assert b"App shell" not in resp.getvalue()


def test_no_matching_mount_renders_default_404(make_urlconf, spa_dir):
    # Mount under /app; a request to /other has no mount -> default 404.
    def ping(request):
        return HttpResponse("pong")

    name = make_urlconf([path("api/ping", ping)], handler404=handler404)
    cfg = [{"prefix": "/app", "directory": str(spa_dir), "fallback": "index.html"}]
    with override_settings(ROOT_URLCONF=name, DJANGO_SPASERVE=cfg):
        resp = Client().get("/other", **BROWSER)
    assert resp.status_code == 404
    assert b"App shell" not in resp.getvalue()

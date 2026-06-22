"""Shared fixtures: throwaway SPA build dirs and dynamic URLconf helpers."""

from __future__ import annotations

import itertools
import sys
import types

import pytest

from django_spaserve import config as _config

_counter = itertools.count()


@pytest.fixture(autouse=True)
def _clear_registry():
    """Strategy A mounts self-register; isolate the registry between tests."""
    _config._REGISTERED_CONFIGS.clear()
    yield
    _config._REGISTERED_CONFIGS.clear()


def _build_dist(root, *, index=True, fallback_404=False, sub_index=True):
    dist = root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "assets" / "app.js").write_text("console.log('app')")
    (dist / "assets" / "style.css").write_text("body{margin:0}")
    if index:
        (dist / "index.html").write_text("<!doctype html><title>App shell</title>")
    if fallback_404:
        (dist / "404.html").write_text("<!doctype html><title>Not found</title>")
    if sub_index:
        sub = dist / "sub"
        sub.mkdir()
        (sub / "index.html").write_text("<!doctype html><title>Sub shell</title>")
    return dist


@pytest.fixture
def spa_dir(tmp_path):
    """A pure SPA build: index.html, assets, and a sub/ dir (no 404.html)."""
    return _build_dist(tmp_path)


@pytest.fixture
def make_dist(tmp_path):
    """Factory to build SPA dirs with specific files present/absent."""
    counter = itertools.count()

    def _make(**kwargs):
        root = tmp_path / f"build{next(counter)}"
        root.mkdir()
        return _build_dist(root, **kwargs)

    return _make


@pytest.fixture
def make_urlconf():
    """Register a throwaway URLconf module and return its dotted name."""
    created = []

    def _make(urlpatterns, handler404=None):
        name = f"tests._dyn_urls_{next(_counter)}"
        module = types.ModuleType(name)
        module.urlpatterns = urlpatterns
        if handler404 is not None:
            module.handler404 = handler404
        sys.modules[name] = module
        created.append(name)
        return name

    yield _make

    for name in created:
        sys.modules.pop(name, None)

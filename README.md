# django-spaserve

> [!IMPORTANT]
> 🤖 **AI coding-agent project** — this package was developed with the assistance of an
> AI coding agent. Please review the code and tests before relying on it in production.

![AI coding-agent project](https://img.shields.io/badge/built%20with-AI%20coding%20agent-8A2BE2)
[![CI](https://github.com/bas-h/django-spaserve/actions/workflows/ci.yml/badge.svg)](https://github.com/bas-h/django-spaserve/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/django-spaserve.svg)](https://pypi.org/project/django-spaserve/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-spaserve.svg)](https://pypi.org/project/django-spaserve/)

Serve a built single-page-application (React / Vue / Svelte `dist/` output) from
Django with correct **client-side-routing fallback** — no nginx/Apache/CDN rewrite
rules required.

`django-spaserve` ports the navigation heuristic from FastAPI's `app.frontend()` feature
to Django, solving the three-way decision every SPA server must get right:

1. The path is a **real built file** (`/assets/app.abc123.js`) → serve it with the
   right content-type and caching.
2. The path is a **client-side route** (`/dashboard/settings`) → serve `index.html`
   with `200` so the JS router can render it.
3. The path is a **genuinely missing asset / API 404** (`/assets/typo.js`) → return a
   real `404`, **not** the SPA shell.

The trick for distinguishing (2) from (3) is a **navigation-request heuristic**: the
shell is served only when the path has no file extension *and* the `Accept` header
looks like a browser HTML navigation. This means `curl` (`*/*`) and browsers get the
shell, a `fetch()` asking for JSON does not, and a missing `.js` always 404s.

## Inspiration & prior art

`django-spaserve` is a port of **FastAPI's `app.frontend()` / `router.frontend()`** feature
(shipped June 2026), which serves a SPA build in one line and replaced the manual
`StaticFiles(html=True)` + catch-all dance. We wanted the same ergonomics for Django.

The whole FastAPI feature lives in one file, and the navigation heuristic — the single
most valuable thing to port faithfully — is copied near-verbatim:

- Feature PR (motivation + design discussion):
  [`fastapi/fastapi#15800`](https://github.com/fastapi/fastapi/pull/15800)
- Reference implementation:
  [`fastapi/routing.py` @ `a497a02`](https://github.com/fastapi/fastapi/blob/a497a025e7114ca442478ed28da7e0a1cdc6177a/fastapi/routing.py#L1942)

How FastAPI's pieces map onto this package:

| FastAPI | Purpose | `django-spaserve` |
|---|---|---|
| `_low_priority_routes` (matched after all real routes) | the SPA never shadows the API | a catch-all `re_path` placed last (Strategy A) **or** `handler404` (Strategy B) — Django has no built-in "match last" bucket |
| `_FrontendStaticFiles.get_response` | the three-way decision | `decide_response()` |
| `_is_frontend_navigation_request` / `_iter_accept_media_types` | nav-vs-asset disambiguation | `navigation.is_navigation_request()` (ported near-verbatim) |
| `_FrontendRoute(Group)`, `_frontend_path_specificity` | multiple SPAs, longest-prefix wins | `spa_urls_multi()` + `SpaConfig.specificity` |
| `_normalize_frontend_path` / `_join_frontend_paths` | prefix normalization | `config.normalize_frontend_path()` / `join_frontend_paths()` |
| `fallback="auto"\|"index.html"\|"404.html"` | SPA vs SSG-export behavior | the same `fallback` param |
| Starlette `StaticFiles(follow_symlink=False)` | traversal/symlink-safe file lookup | `files.lookup_path()` (`os.path.realpath` + containment check) |
| `check_dir` `RuntimeError` (resolved abs path) | startup validation | Django system checks (`django_spaserve.checks`) |

The same `frontend` motivation appears in other frameworks; this is the Django take on
the idea. Credit for the design and the heuristic goes to the FastAPI authors.

## Install

```bash
pip install django-spaserve
```

Requires **Django ≥ 4.2** and **Python ≥ 3.10**. No dependencies beyond Django.

## Quickstart

### Strategy A — catch-all (great for dev & single-SPA-at-root)

`spa_urls()` serves both real files and the shell fallback itself. Put it **last** in
your root `urlpatterns` — anything `include()`d after it is shadowed.

```python
# urls.py
from django.contrib import admin
from django.urls import path, include
from django_spaserve import spa_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("myapi.urls")),
    *spa_urls("/", directory=BASE_DIR / "frontend/dist"),  # MUST be last
]
```

### Strategy B — `handler404` (the blessed production setup)

Django invokes `handler404` only after every real route has failed to match, so it
**cannot shadow your API**. Pair it with [WhiteNoise](https://whitenoise.readthedocs.io/)
(or a CDN) serving the hashed asset files; `django-spaserve` then only decides shell-vs-404.

```python
# settings.py
DJANGO_SPASERVE = [
    {"prefix": "/", "directory": BASE_DIR / "frontend/dist", "fallback": "index.html"},
]
INSTALLED_APPS = [..., "django_spaserve"]   # optional: enables `manage.py check` validation

# urls.py
handler404 = "django_spaserve.handler404"
```

| | Strategy A (`spa_urls`) | Strategy B (`handler404`) |
|---|---|---|
| Serves real files | ✅ yes | ❌ no (use WhiteNoise/CDN) |
| Can shadow the API | ⚠️ if placed wrong | ✅ never |
| Best for | dev, single SPA at `/` | production behind WhiteNoise/CDN |

## Fallback modes

`fallback` controls what happens when no real file matches:

- `"auto"` *(default)* — if `404.html` exists, serve it (with a `404`) for **every**
  miss; otherwise serve `index.html` for navigations. Best for SPAs that don't ship a
  `404.html`, and for static-site exports that do.

  > **Note:** in `auto` mode a present `404.html` takes precedence over the shell, so
  > client-side deep links (`/dashboard/settings`) would render `404.html` rather than
  > the app. If your SPA handles its own routing, either omit `404.html` or set
  > `fallback="index.html"` explicitly. (This matches FastAPI's `app.frontend()`.)
- `"index.html"` — always serve the shell for navigations (classic SPA).
- `"404.html"` — always serve `404.html` with a `404` status (static-site export).
- `None` — never fall back; missing paths always `404`.

## Multiple SPAs

Mount several builds at different prefixes; the most specific (longest) prefix wins.

```python
# Strategy A
urlpatterns = [
    path("api/", include("myapi.urls")),
    *spa_urls_multi([
        {"prefix": "/admin-spa", "directory": BASE_DIR / "admin/dist"},
        {"prefix": "/", "directory": BASE_DIR / "app/dist"},
    ]),
]

# Strategy B
DJANGO_SPASERVE = [
    {"prefix": "/admin-spa", "directory": BASE_DIR / "admin/dist"},
    {"prefix": "/", "directory": BASE_DIR / "app/dist"},
]
```

`/admin-spa/users` hits the admin build; `/dashboard` hits the root build. Ordering is
handled for you (longest-prefix-first), regardless of how you list the mounts.

## Production notes

- **Preferred setup:** WhiteNoise serves the hashed assets (compression + far-future
  caching); `django-spaserve` handles only the shell fallback via `handler404`. This splits
  "serve real files fast" from "decide shell vs 404" cleanly.
- **Never cache `index.html`.** The shell is served with `Cache-Control: no-cache` by
  default (`index_cache_control`) so users never get a stale app after a deploy. Cache
  hashed assets aggressively (`asset_cache_control`, or let WhiteNoise do it).
- If a CDN/edge already does SPA rewrites, this app is a harmless no-op fallback for
  origin requests and still gives you a correct local-dev experience.
- Security headers (CSP, etc.) are out of scope — see [`django-csp`](https://django-csp.readthedocs.io/).
  For CSP-nonce or runtime-env injection into the shell, use the optional `html_transform`
  hook (off by default):

  ```python
  def inject_nonce(html: bytes, request) -> bytes:
      return html.replace(b"__CSP_NONCE__", request.csp_nonce.encode())

  spa_urls("/", directory=DIST, html_transform=inject_nonce)
  ```

## Configuration reference (`SpaConfig`)

| field | default | meaning |
|---|---|---|
| `directory` | — | the SPA build output directory (required) |
| `prefix` | `"/"` | URL prefix to mount at |
| `fallback` | `"auto"` | `"auto"` / `"index.html"` / `"404.html"` / `None` |
| `check_dir` | `True` | validate directory/fallback existence at startup |
| `index_cache_control` | `"no-cache"` | `Cache-Control` for the shell |
| `asset_cache_control` | `None` | `Cache-Control` for real files |
| `html_transform` | `None` | `(html_bytes, request) -> bytes` shell transform |

## How it works

The navigation heuristic and three-way decision are faithful ports of FastAPI's
[`_is_frontend_navigation_request`](https://github.com/fastapi/fastapi/blob/a497a025e7114ca442478ed28da7e0a1cdc6177a/fastapi/routing.py#L1921)
and
[`_FrontendStaticFiles.get_response`](https://github.com/fastapi/fastapi/blob/a497a025e7114ca442478ed28da7e0a1cdc6177a/fastapi/routing.py#L1842)
(see [Inspiration & prior art](#inspiration--prior-art)). The `Accept`-header `q`-value
parsing matches FastAPI's use of `email.message.Message`. File lookup refuses path
traversal and symlink escapes (`os.path.realpath` + containment check, mirroring
Starlette's `follow_symlink=False`). Only `GET`/`HEAD` are allowed; other methods
get `405`. A complete, runnable Django + Vite/React example lives in [`example/`](./example).

## Development

```bash
pip install -e ".[dev]"
pytest                    # run the test suite
ruff check . && ruff format --check .
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the suite across
Python 3.10–3.13 × Django 4.2/5.0/5.1/5.2, lints with ruff, and builds the example SPA.

### Releasing

Publishing is automated via [`.github/workflows/release.yml`](.github/workflows/release.yml)
using **PyPI Trusted Publishing** (OIDC — no tokens). To cut a release:

1. Bump `version` in `pyproject.toml`.
2. Tag and push: `git tag vX.Y.Z && git push --tags` (the build job verifies the tag
   matches the package version).
3. Publish a **GitHub Release** for that tag — the `publish` job uploads to PyPI and
   attaches the sdist/wheel to the release.

One-time setup: add a trusted publisher on PyPI (repo `bas-h/django-spaserve`, workflow
`release.yml`, environment `pypi`) and create a `pypi` environment in the repo settings.

## Credits & license

Ported from [FastAPI](https://github.com/fastapi/fastapi)'s `app.frontend()` feature
([PR #15800](https://github.com/fastapi/fastapi/pull/15800)) — design and the navigation
heuristic are theirs. FastAPI and Starlette are MIT-licensed.

This package is released under the **MIT License** (see [`LICENSE`](./LICENSE)).

Developed with the assistance of an AI coding agent.

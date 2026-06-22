# django-spaserve example

A minimal end-to-end example: a real Vite + React (react-router) SPA served by
Django through `django-spaserve` using **Strategy A** (catch-all `spa_urls`).

```
example/
├── manage.py
├── project/            # Django project (settings, urls, wsgi)
└── frontend/           # Vite + React app
    └── dist/           # the built SPA that Django serves (npm run build)
```

## Run it

From the repository root, install the package and Django, then start the server:

```bash
pip install -e .            # installs django-spaserve
pip install Django

cd example
# Build the SPA (only needed if you change anything under frontend/src):
( cd frontend && npm install && npm run build )

python manage.py check      # validates the SPA mount (directory/fallback exist)
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and click around. Everything below is wired up:

| Request | Result |
|---|---|
| `GET /` | `index.html` (the React shell) |
| `GET /about`, `GET /dashboard/settings` | `index.html` — client-side routes (reload them: deep-linking works) |
| `GET /assets/index-*.js` | the real hashed bundle, `text/javascript`, with `ETag`/`Last-Modified` |
| `GET /assets/typo.js` | a real **404** — a missing asset is *not* turned into HTML |
| `GET /api/ping` | `{"message": "pong from Django"}` — the API is never shadowed |
| `fetch()` with `Accept: application/json` to an unknown path | **404**, not the shell |
| `POST /about` | **405** |

The shell is served with `Cache-Control: no-cache` so a redeploy never leaves users
on a stale app; the hashed bundle supports conditional GET (`304 Not Modified`).

## Switching to the production setup (Strategy B)

In production you typically let WhiteNoise/CDN serve the hashed assets and use
`django-spaserve` only for the shell fallback. See the commented block at the bottom of
`project/settings.py` and `project/urls.py` for the `handler404` + `DJANGO_SPASERVE` wiring.

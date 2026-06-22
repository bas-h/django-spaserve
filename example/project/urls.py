"""URL configuration for the example project.

The real API routes are matched first; `spa_urls()` is the catch-all placed LAST
so it never shadows them but handles every client-side route + asset.
"""

from django.http import JsonResponse
from django.urls import include, path

from django_spaserve import spa_urls

from .settings import FRONTEND_DIST


def ping(request):
    """A tiny real API endpoint to prove the SPA never shadows the backend."""
    return JsonResponse({"message": "pong from Django", "path": request.path})


api_urls = ([path("ping", ping)], "api")

urlpatterns = [
    path("api/", include(api_urls)),
    # Catch-all: serves /assets/*.js files AND falls back to index.html for
    # client-side routes like /about and /dashboard. MUST be last.
    *spa_urls("/", directory=FRONTEND_DIST, fallback="auto"),
]

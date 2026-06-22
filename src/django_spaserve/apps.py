"""AppConfig — registers system checks when ``django_spaserve`` is installed.

Adding ``"django_spaserve"`` to ``INSTALLED_APPS`` is optional; it is only needed to
get directory/fallback validation via ``manage.py check``. The serving behavior
works without it.
"""

from __future__ import annotations

from django.apps import AppConfig
from django.core.checks import register


class DjangoSpaConfig(AppConfig):
    name = "django_spaserve"
    verbose_name = "Django SPA"

    def ready(self) -> None:
        from .checks import check_spa_configs

        register(check_spa_configs)

"""Django system checks — port of FastAPI's ``check_dir`` validation.

Validates, at ``manage.py check`` / startup time, that each configured mount's
directory exists and (for ``index.html`` / ``404.html`` fallbacks) that the
fallback file is present. Error messages include the **resolved absolute path**
to make misconfiguration easy to debug, mirroring FastAPI's ``RuntimeError`` text.
"""

from __future__ import annotations

import os
from typing import List

from django.core.checks import Error

from .config import SpaConfig, iter_registered_configs, resolved_absolute_path

__all__ = ["validate_config", "check_spa_configs"]


def validate_config(config: SpaConfig) -> List[str]:
    """Return a list of human-readable problems with ``config`` (empty if OK)."""
    problems: List[str] = []
    directory = config.directory
    if not os.path.isdir(directory):
        problems.append(
            f"Frontend directory '{directory}' does not exist. "
            f"Resolved absolute path: '{resolved_absolute_path(directory)}'"
        )
        return problems
    if config.fallback in {"index.html", "404.html"}:
        fallback_path = os.path.join(directory, config.fallback)
        if not os.path.isfile(fallback_path):
            problems.append(
                f"Frontend fallback file '{config.fallback}' does not exist in "
                f"directory '{directory}'. Resolved absolute directory: "
                f"'{resolved_absolute_path(directory)}'"
            )
    return problems


def _all_configs() -> List[SpaConfig]:
    # Strategy A mounts register themselves; Strategy B mounts live in settings.
    from .handlers import load_settings_configs

    return [*iter_registered_configs(), *load_settings_configs()]


def check_spa_configs(app_configs, **kwargs) -> List[Error]:
    """System check registered by :class:`django_spaserve.apps.DjangoSpaConfig`."""
    errors: List[Error] = []
    for index, config in enumerate(_all_configs()):
        if not config.check_dir:
            continue
        for problem in validate_config(config):
            errors.append(
                Error(
                    problem,
                    obj=f"django_spaserve mount '{config.prefix}'",
                    id=f"django_spaserve.E{index:03d}",
                )
            )
    return errors

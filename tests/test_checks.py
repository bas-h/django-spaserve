"""System checks and eager validation."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from django_spaserve import SpaConfig, spa_urls
from django_spaserve.checks import check_spa_configs, validate_config


def test_spa_urls_raises_on_missing_directory(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ImproperlyConfigured) as exc:
        spa_urls("/", directory=missing)
    # Error message includes the resolved absolute path for debugging.
    assert str(missing.resolve()) in str(exc.value)


def test_check_dir_false_skips_validation(tmp_path):
    missing = tmp_path / "does-not-exist"
    # Should not raise even though the directory is absent.
    patterns = spa_urls("/", directory=missing, check_dir=False)
    assert patterns


def test_validate_config_reports_missing_fallback_file(make_dist):
    dist = make_dist(fallback_404=False)  # no 404.html
    config = SpaConfig(directory=dist, fallback="404.html")
    problems = validate_config(config)
    assert problems
    assert "404.html" in problems[0]
    assert str(dist.resolve()) in problems[0]


def test_validate_config_ok_for_complete_build(spa_dir):
    config = SpaConfig(directory=spa_dir, fallback="index.html")
    assert validate_config(config) == []


def test_system_check_flags_bad_settings_mount(tmp_path):
    missing = tmp_path / "nope"
    with override_settings(DJANGO_SPASERVE=[{"prefix": "/", "directory": str(missing)}]):
        errors = check_spa_configs(app_configs=None)
    assert errors
    assert errors[0].id.startswith("django_spaserve.E")
    assert str(missing.resolve()) in errors[0].msg


def test_system_check_passes_for_good_mount(spa_dir):
    with override_settings(
        DJANGO_SPASERVE=[
            {"prefix": "/", "directory": str(spa_dir), "fallback": "index.html"}
        ]
    ):
        errors = check_spa_configs(app_configs=None)
    assert errors == []

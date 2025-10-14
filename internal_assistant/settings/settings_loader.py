import functools
import logging
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic.v1.utils import deep_update, unique_list

from internal_assistant.constants import PROJECT_ROOT_PATH
from internal_assistant.settings.yaml import load_yaml_with_envvars
from internal_assistant.utils.version_check import validate_dependency_versions

logger = logging.getLogger(__name__)

_settings_folder = os.environ.get("PGPT_SETTINGS_FOLDER", PROJECT_ROOT_PATH / "config")

# if running in unittest, use the test profile
_test_profile = ["test"] if "tests.fixtures" in sys.modules else []

active_profiles: list[str] = unique_list(
    ["default"]
    + [
        item.strip()
        for item in os.environ.get("PGPT_PROFILES", "").split(",")
        if item.strip()
    ]
    + _test_profile
)


def merge_settings(settings: Iterable[dict[str, Any]]) -> dict[str, Any]:
    return functools.reduce(deep_update, settings, {})


def load_settings_from_profile(profile: str) -> dict[str, Any]:
    if profile == "default":
        profile_file_name = "settings.yaml"
    else:
        # Check for environment-specific configs first
        env_path = Path(_settings_folder) / "environments" / f"{profile}.yaml"
        if env_path.exists():
            path = env_path
        else:
            # Check for model-specific configs
            model_path = Path(_settings_folder) / "models" / f"{profile}.yaml"
            if model_path.exists():
                path = model_path
            else:
                # Fallback to old naming convention for backward compatibility
                profile_file_name = f"settings-{profile}.yaml"
                path = Path(_settings_folder) / profile_file_name

    if profile == "default":
        path = Path(_settings_folder) / profile_file_name

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with Path(path).open("r", encoding="utf-8") as f:
        config = load_yaml_with_envvars(f)
    if not isinstance(config, dict):
        raise TypeError(f"Config file has no top-level mapping: {path}")
    return config


def load_active_settings() -> dict[str, Any]:
    """Load active profiles and merge them."""
    logger.info("Starting application with profiles=%s", active_profiles)

    # Validate dependency versions before loading settings
    validate_dependency_versions()

    loaded_profiles = [
        load_settings_from_profile(profile) for profile in active_profiles
    ]
    merged: dict[str, Any] = merge_settings(loaded_profiles)
    return merged

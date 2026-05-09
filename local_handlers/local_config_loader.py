#!/usr/bin/env python3
"""Local module to support YAML-based configuration loading."""
import os
from typing import Any

import yaml

__all__ = ["load_core_config"]

CONFIG_PATH = "./my_data/core_configuration.yml"


def load_core_config() -> dict[str, Any]:
    """Load the core configuration from the YAML file.

    Returns:
        Configuration dictionary containing all settings from core_configuration.yml.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        yaml.YAMLError: If the configuration file contains invalid YAML.
    """
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"core_configuration.yml missing at {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as config_file:
        return yaml.safe_load(config_file)

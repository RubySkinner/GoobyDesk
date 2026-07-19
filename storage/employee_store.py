#!/usr/bin/env python3
"""Employee authentication JSON store wrapper."""

from __future__ import annotations

from typing import Any

from local_handlers.local_config_loader import load_core_config
from storage.json_store import JsonStore
from storage.validator import is_list


class EmployeeStore:
    """Storage wrapper for employee auth records."""

    def __init__(self, file_path: str) -> None:
        self.store = JsonStore(file_path=file_path, default_factory=list, validator=is_list)

    @classmethod
    def from_config(cls) -> "EmployeeStore":
        config = load_core_config()
        return cls(config["core"]["employee_auth_file"])

    def load_all(self) -> list[dict[str, Any]]:
        employees = self.store.read(default=[])
        return employees if isinstance(employees, list) else []

    def save_all(self, employees: list[dict[str, Any]]) -> None:
        self.store.write(employees)

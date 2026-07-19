#!/usr/bin/env python3
# JSON Storage Wrapper for change request records.
from __future__ import annotations
from typing import Any
from local_handlers.local_config_loader import load_core_config
from storage.json_store import JsonStore
from storage.validator import is_list

class ChangesStore:
    """Storage wrapper for change request records."""
    def __init__(self, file_path: str) -> None:
        self.store = JsonStore(file_path=file_path, default_factory=list, validator=is_list)

    @classmethod
    def from_config(cls) -> "ChangesStore":
        config = load_core_config()
        return cls(config["core"]["changes_file"])

    def load_all(self) -> list[dict[str, Any]]:
        records = self.store.read(default=[])
        return records if isinstance(records, list) else []

    def save_all(self, records: list[dict[str, Any]]) -> None:
        self.store.write(records)

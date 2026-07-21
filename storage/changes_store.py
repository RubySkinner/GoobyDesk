#!/usr/bin/env python3
# JSON Storage Wrapper for change request records.
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

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
        if not isinstance(records, list):
            return []
        return [record for record in records if isinstance(record, dict)]

    def save_all(self, records: list[dict[str, Any]]) -> None:
        self.store.write(records)

    def append(self, record: dict[str, Any]) -> None:
        self.store.append(record)

    def get_by_change_number(self, change_number: str) -> dict[str, Any] | None:
        return next(
            (record for record in self.load_all() if record.get("change_number") == change_number),
            None,
        )

    def update(self, change_number: str, updater: Callable[[Any], Any]) -> bool:
        def predicate(record: Any) -> bool:
            return isinstance(record, dict) and record.get("change_number") == change_number

        _, updated = self.store.update(predicate, updater)
        return updated

    def delete(self, change_number: str) -> int:
        def predicate(record: Any) -> bool:
            return isinstance(record, dict) and record.get("change_number") == change_number

        _, deleted = self.store.delete(predicate)
        return deleted

    def next_change_number(self, year: int | None = None) -> str:
        current_year = year or datetime.now().year
        prefix = f"CHG-{current_year}-"
        existing_numbers = [
            int(record["change_number"].rsplit("-", 1)[-1])
            for record in self.load_all()
            if isinstance(record.get("change_number"), str)
            and record["change_number"].startswith(prefix)
            and record["change_number"].rsplit("-", 1)[-1].isdigit()
        ]
        next_sequence = max(existing_numbers, default=0) + 1
        return f"{prefix}{next_sequence:04d}"

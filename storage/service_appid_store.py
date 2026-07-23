#!/usr/bin/env python3
"""Service/App ID storage wrapper.

Manages persistence and normalization for service-to-app-id mappings.
Accepts either a single dict or a list of dicts and normalizes to a
list of dicts for callers.
"""
from __future__ import annotations
from typing import Any
from local_handlers.local_config_loader import load_core_config
from storage.json_store import JsonStore
from storage.validator import is_list

class ServiceAppIdStore:
    """Storage wrapper for service/app ID records."""

    def __init__(self, file_path: str) -> None:
        self.store = JsonStore(file_path=file_path, default_factory=list, validator=is_list)
    @classmethod
    def from_config(cls) -> "ServiceAppIdStore":
        config = load_core_config()
        return cls(config["core"]["serviceid_appid_file"])

    def load_all(self) -> list[dict[str, Any]]:
        # Normalize payload to a list of dicts so callers always receive
        # an iterable collection even when the backing file contains a
        # single dict (legacy formats) or a list.
        records = self.store.read(default=[])
        if isinstance(records, dict):
            return [records]
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
        return []

    def save_all(self, records: list[dict[str, Any]]) -> None:
        normalized = self._normalize_records(records)
        self.store.write(normalized)

    @staticmethod
    def _normalize_records(records: list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(records, dict):
            return [records]
        if isinstance(records, list):
            return [record for record in records if isinstance(record, dict)]
        return []

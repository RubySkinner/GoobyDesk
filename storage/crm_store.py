#!/usr/bin/env python3
"""CRM storage wrapper.

Provides customer-specific helpers (ID generation, load/save) on top
of JsonStore. Keeps customer numbering logic and persistence central.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from local_handlers.local_config_loader import load_core_config
from storage.json_store import JsonStore
from storage.validator import is_list

class CrmStore:
    def __init__(self, file_path: str) -> None:
        self.store = JsonStore(file_path=file_path, default_factory=list, validator=is_list)

    @classmethod
    def from_config(cls) -> "CrmStore":
        config = load_core_config()
        return cls(config["core"]["customers_file"])

    def load_all(self) -> list[dict[str, Any]]:
        # Returns a list of customer dicts or an empty list when store is malformed.
        customers = self.store.read(default=[])
        return customers if isinstance(customers, list) else []

    def save_all(self, customers: list[dict[str, Any]]) -> None:
        # Persist full customer list atomically.
        self.store.write(customers)

    def next_customer_id(self, customers: list[dict[str, Any]] | None = None) -> str:
        all_customers = customers if customers is not None else self.load_all()
        current_year = datetime.now(timezone.utc).year
        year_prefix = f"CID-{current_year}-"
        existing_ids = [
            customer.get("customer_id", "")
            for customer in all_customers
            if customer.get("customer_id", "").startswith(year_prefix)
        ]
        next_sequence = len(existing_ids) + 1
        return f"{year_prefix}{next_sequence:04d}"

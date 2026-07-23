#!/usr/bin/env python3
# JSON Storage Wrapper for ticket operations.
from __future__ import annotations
from datetime import datetime
from typing import Any
from local_handlers.local_config_loader import load_core_config
from storage.json_store import JsonStore
from storage.validator import is_list

class TicketStore:
    def __init__(self, file_path: str) -> None:
        self.store = JsonStore(file_path=file_path, default_factory=list, validator=is_list)

    @classmethod
    def from_config(cls) -> "TicketStore":
        config = load_core_config()
        return cls(config["core"]["tickets_file"])

    def load_all(self) -> list[dict[str, Any]]:
        tickets = self.store.read(default=[])
        if not isinstance(tickets, list):
            return []
        return [self._normalize_ticket(ticket) for ticket in tickets]

    def save_all(self, tickets: list[dict[str, Any]]) -> None:
        normalized = [self._normalize_ticket(ticket) for ticket in tickets]
        self.store.write(normalized)

    def append(self, ticket: dict[str, Any]) -> None:
        self.store.append(self._normalize_ticket(ticket))

    def update(
        self,
        predicate: callable,
        updater: callable,
    ) -> bool:
        """Update first matching ticket using predicate and updater.

        Updater receives a shallow-copied record and should return the
        modified record (or None to leave unchanged). Returns True when
        a record was changed.
        """
        def _updater(record: dict[str, Any]):
            copy = dict(record)
            replacement = updater(copy)
            if replacement is None:
                return record
            return self._normalize_ticket(replacement)

        _, changed = self.store.update(predicate, _updater)
        return changed

    def delete(self, predicate: callable) -> int:
        """Delete tickets matching predicate. Returns number removed."""
        _, removed = self.store.delete(predicate)
        return removed

    def update_by_number(self, ticket_number: str, updater: callable) -> bool:
        """Convenience: update ticket by `ticket_number`. Returns True if changed."""
        return self.update(lambda r: r.get("ticket_number") == ticket_number, updater)

    def next_ticket_number(self, year: int | None = None) -> str:
        current_year = year or datetime.now().year
        ticket_count = len(self.load_all()) + 1
        return f"TKT-{current_year}-{ticket_count:04d}"

    def next_change_number(self, year: int | None = None) -> str:
        current_year = year or datetime.now().year
        ticket_count = len(self.load_all()) + 1
        return f"CHG-{current_year}-{ticket_count:04d}"

    @staticmethod
    def _normalize_ticket(ticket: dict[str, Any]) -> dict[str, Any]:
        ticket.setdefault("ticket_notes", [])
        ticket.setdefault("ticket_worknotes", list(ticket.get("ticket_notes", [])))
        ticket.setdefault("ticket_resolution_notes", [])
        return ticket

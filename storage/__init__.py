#!/usr/bin/env python3
"""Shared JSON storage package for GoobyDesk."""

from storage.crm_store import CrmStore
from storage.changes_store import ChangesStore
from storage.employee_store import EmployeeStore
from storage.hr_store import HrStore
from storage.json_store import JsonStore
from storage.service_appid_store import ServiceAppIdStore
from storage.ticket_store import TicketStore

__all__ = [
    "JsonStore",
    "TicketStore",
    "EmployeeStore",
    "CrmStore",
    "HrStore",
    "ChangesStore",
    "ServiceAppIdStore",
]

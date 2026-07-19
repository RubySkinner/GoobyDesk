#!/usr/bin/env python3
"""Validation helpers for JSON stores."""
from __future__ import annotations
from typing import Any

def is_list(data: Any) -> bool:
    """Return True when data is a list."""
    return isinstance(data, list)

def is_dict(data: Any) -> bool:
    """Return True when data is a dict."""
    return isinstance(data, dict)

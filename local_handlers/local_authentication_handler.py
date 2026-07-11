#!/usr/bin/env python3
# Local module to support secure authentication handling.
# local_handlers/local_authentication_handler.py
from .goobydesk_standard_library import hash_password, verify_password
__all__ = ["hash_password", "verify_password"]

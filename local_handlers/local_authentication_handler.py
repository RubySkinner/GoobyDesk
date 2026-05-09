#!/usr/bin/env python3
"""Local module to support secure authentication handling with bcrypt."""
import bcrypt

__all__ = ["hash_password", "verify_password"]


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt with 12 rounds.

    Args:
        plain_password: The plain text password to hash.

    Returns:
        The bcrypt hash as a string, safe for storage.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed_user_password = bcrypt.hashpw(plain_password.encode(), salt)
    return hashed_user_password.decode()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain text password against a stored bcrypt hash.

    Args:
        plain_password: The plain text password to verify.
        stored_hash: The stored bcrypt hash to check against.

    Returns:
        True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode(),
        stored_hash.encode()
    )

#!/usr/bin/env python3
"""Generate a cryptographically secure Flask secret key."""
import secrets
import string


def generate_flask_secret_key(length: int = 30) -> str:
    """Generate a cryptographically secure random string for Flask.

    Args:
        length: The length of the secret key to generate.

    Returns:
        A random string of uppercase letters and digits.
    """
    alphabet = string.ascii_uppercase + string.digits
    secret_key = "".join(secrets.choice(alphabet) for _ in range(length))
    return secret_key


def main() -> None:
    """Generate and print a new Flask secret key with usage instructions."""
    key = generate_flask_secret_key()
    print(f"GENERATED NEW {key}")
    print(f"\nAdd this to your .env file or configuration:")
    print(f"FLASKAPP_SECRET_KEY={key}")


if __name__ == "__main__":
    main()

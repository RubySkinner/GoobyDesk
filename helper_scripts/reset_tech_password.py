#!/usr/bin/env python3
"""Password reset utility for GoobyDesk technicians."""
import getpass
import json
import sys
from typing import Any

import local_handlers.local_config_loader as local_config_loader

EmployeeDict = dict[str, Any]


def load_employees() -> tuple[list[EmployeeDict], str]:
    """Load employees from the JSON database file.

    Returns:
        Tuple of (employee list, file path).

    Raises:
        SystemExit: If the file cannot be found or parsed.
    """
    core_yaml_config = local_config_loader.load_core_config()
    employee_file: str = core_yaml_config["employee_file"]

    try:
        with open(employee_file, "r") as f:
            return json.load(f), employee_file
    except FileNotFoundError:
        print(f"ERROR: Employee JSON Database not found: {employee_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("ERROR: Employee JSON Database is not valid JSON")
        sys.exit(1)


def save_employees(employees: list[EmployeeDict], employee_file: str) -> None:
    """Save employees to the JSON database file.

    Args:
        employees: List of employee dictionaries to save.
        employee_file: Path to the employee JSON file.
    """
    with open(employee_file, "w") as f:
        json.dump(employees, f, indent=4)


def reset_password(username: str, new_password: str) -> None:
    """Reset the password for a technician.

    Sets the legacy tech_authcode which will auto-migrate to
    a secure hash on next login.

    Args:
        username: The technician username.
        new_password: The new plain text password.

    Raises:
        SystemExit: If the user is not found.
    """
    employees, employee_file = load_employees()

    user_found = False
    for employee in employees:
        if employee.get("tech_username") == username:
            user_found = True

            if "password_hash" in employee:
                del employee["password_hash"]

            employee["tech_authcode"] = new_password

            print(f"Password reset for user: {username}")
            print("  - Removed password_hash")
            print("  - Set tech_authcode (will auto-migrate on next login)")
            break

    if not user_found:
        print(f"ERROR: User '{username}' not found in employee database")
        sys.exit(1)

    save_employees(employees, employee_file)
    print(f"Changes saved to {employee_file}")
    print("\nThe user can now log in with the new password, and it will")
    print("automatically be migrated to a secure password_hash.")


def main() -> None:
    """Interactive password reset workflow."""
    print("=" * 60)
    print("GoobyDesk Technician Password Reset Tool")
    print("=" * 60)
    print()

    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter technician username: ").strip()

    if not username:
        print("ERROR: Username cannot be empty")
        sys.exit(1)

    print()
    new_password = getpass.getpass("Enter new password: ")
    confirm_password = getpass.getpass("Confirm new password: ")

    if new_password != confirm_password:
        print("ERROR: Passwords do not match")
        sys.exit(1)

    if len(new_password) < 8:
        print("WARNING: Password is less than 8 characters")
        confirm = input("Continue anyway? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Password reset cancelled")
            sys.exit(0)

    print()
    print(f"Resetting password for: {username}")
    confirm = input("Are you sure? (yes/no): ").strip().lower()

    if confirm != "yes":
        print("Password reset cancelled")
        sys.exit(0)

    print()
    reset_password(username, new_password)


if __name__ == "__main__":
    main()

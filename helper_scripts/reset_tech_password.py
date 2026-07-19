#!/usr/bin/env python3
# Reset a technicians password using the legacy authentication method.
import sys
import getpass

from local_handlers.local_config_loader import load_core_config
from storage.employee_store import EmployeeStore


core_yaml_config = load_core_config()
employee_store = EmployeeStore(core_yaml_config["core"]["employee_auth_file"])

def load_employees():
    return employee_store.load_all(), str(employee_store.store.path)

def save_employees(employees, employee_file):
    _ = employee_file
    employee_store.save_all(employees)

def reset_password(username, new_password):
    employees, employee_file = load_employees()
    
    user_found = False
    for employee in employees:
        if employee.get("tech_username") == username:
            user_found = True
            
            # Remove password_hash if it exists
            if "password_hash" in employee:
                del employee["password_hash"]
            
            # Set legacy tech_authcode
            employee["tech_authcode"] = new_password
            
            print(f"✓ Password reset for user: {username}")
            print(f"  - Removed password_hash")
            print(f"  - Set tech_authcode (will auto-migrate on next login)")
            break
    
    if not user_found:
        print(f"ERROR: User '{username}' not found in employee database")
        sys.exit(1)
    
    save_employees(employees, employee_file)
    print(f"✓ Changes saved to {employee_file}")
    print("\nThe user can now log in with the new password, and it will")
    print("automatically be migrated to a secure password_hash.")

def main():
    print("=" * 60)
    print("GoobyDesk Technician Password Reset Tool")
    print("=" * 60)
    print()
    
    # Get username
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        username = input("Enter technician username: ").strip()
    
    if not username:
        print("ERROR: Username cannot be empty")
        sys.exit(1)
    
    # Get new password
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
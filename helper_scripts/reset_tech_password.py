#!/usr/bin/env python3
#!/usr/bin/env python3
"""Deprecated helper: reset_tech_password

This script has been deprecated. Use the admin password-reset
functionality available in the HR UI (`POST /hr/employee/<uuid>/reset-password`)
which is audited and only accessible to users with the `admin` role.

Keeping this file for historical reference only.
"""
import sys


def main():
    print("This script is deprecated.")
    print("Use the HR admin UI to reset technician passwords instead.")
    sys.exit(1)


if __name__ == "__main__":
    main()
# Project Roadmap

## 0.9.9-X

Remove duplicate logic in the webhook module to simplify new implementations. **Example:**

```python3
def create_api_ticket(
    requestor_name,
    requestor_email,
    subject,
    message,
    request_type,
    impact,
    urgency,
):
```

Implement Standardized JSON storage layer. **Generic Example:**

```python3
from pathlib import Path
import json
DATA_DIR = Path("data")
class JsonStore:

    def __init__(self, filename):
        self.path = DATA_DIR / f"{filename}.json"

    def read(self):
        if not self.path.exists():
            return []

        with open(self.path, "r", encoding="utf-8") as fp:
            return json.load(fp)

    def write(self, data):
        with open(self.path, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4)
```

Build out the JSON storage layer to look like

```python3
JsonStore.read()
JsonStore.write()
JsonStore.append()
JsonStore.update()
JsonStore.delete()
JsonStore.backup()
JsonStore.validate()
JsonStore.lock()
JsonStore.exists()
JsonStore.atomic_write()
```

## 1.0.0

Pending

## 1.1.0

High quality centralized json storage layer with individual module support. **Example:**

```txt
storage/
├── __init__.py
├── base_store.py          # Common interface
├── json_store.py          # Generic JSON implementation
├── ticket_store.py        # Ticket-specific operations
├── employee_store.py      # Employee-specific operations
├── crm_store.py
├── asset_store.py
├── alert_store.py
├── backup.py
├── validator.py
└── file_lock.py
```
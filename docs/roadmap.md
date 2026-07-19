# Project Roadmap

## 0.9.9-X

Remove duplicate logic in the webhook module to simplify new implementations. **Example:** Index.html/app.py

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

Simplify CRM Customer Creation. **Example:**

```python3
def build_customer_record(form, technician, customers):
    ...
    return customer
```

then something like

```python3
customers = load_customers_file()

customer = build_customer_record(
    request.form,
    session["technician"],
    customers
)

customers.append(customer)

save_customers_file(customers)
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

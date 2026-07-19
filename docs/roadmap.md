# Project Roadmap

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

Consider a basic refactor to use `local_handlers/utils.py` as the authentication handler.

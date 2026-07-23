#!/usr/bin/env python3
from typing import Dict, Any

def build_customer_record(form: Dict[str, Any]) -> Dict[str, Any]:
    """Build a customer record from sanitized form data.

    This function does not set persistence-specific fields like `uuid` or
    `customer_id` - the caller should add those.
    """
    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()
    preferred_name = (form.get("preferred_name") or first_name).strip()
    email = (form.get("email") or "").strip().lower()

    record: Dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "preferred_name": preferred_name,
        "company": form.get("company") or None,
        "job_title": form.get("job_title") or None,
        "email": email,
        "phone": form.get("phone") or None,
        "address": {
            "street": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": form.get("country") or "US",
        },
        "timezone": form.get("timezone") or "UTC",
        "language": "en-US",
        "discord": {
            "username": form.get("discord_username") or None,
            "user_id": None,
        },
        "minecraft": {
            "username": form.get("minecraft_username") or None,
            "uuid": None,
        },
        "last_seen": None,
        "last_login": None,
        "status": form.get("status", "active"),
        "status_reason": None,
        "account_locked": False,
        "email_verified": False,
        "mfa_enabled": False,
        "customer_type": form.get("customer_type", "individual"),
        "account_tier": form.get("account_tier", "basic"),
        "vip": "vip" in form,
        "content_creator": "content_creator" in form,
        "risk_level": "low",
        "lifetime_value": 0.00,
        "billing_currency": "USD",
        "preferred_contact": form.get("preferred_contact", "email"),
        "marketing_opt_in": "marketing_opt_in" in form,
        "maintenance_notifications": "maintenance_notifications" in form,
        "assigned_account_manager": None,
        "services": [],
        "licenses": [],
        "domains": [],
        "servers": [],
        "support_contract": {"enabled": False, "sla": None, "expires": None},
        "custom_fields": {},
        "account_tags": [],
        "crm_worknotes": [],
    }

    # Allow extensions to massage the record later
    return record

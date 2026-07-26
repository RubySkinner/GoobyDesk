#!/usr/bin/env python3
import logging
import uuid
import hashlib
import os

from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, Response, current_app, flash
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH
from storage.crm_store import CrmStore
from local_handlers.crm_helpers import build_customer_record
from local_handlers.validation import require_fields, is_valid_email

crm_module_bp = Blueprint('crm_module', __name__, url_prefix='/crm')

# NOTE: use @role_required(ROLE_ITSM_TECH) on routes requiring ITSM technicians

def _get_crm_store():
    """Return a CrmStore instance using loaded config or legacy loader."""
    core_cfg = current_app.config.get("LOADED_CONFIG")
    if core_cfg is None:
        # fallback: try legacy loader
        from local_handlers.local_config_loader import load_core_config
        core_cfg = load_core_config()
    customers_file = core_cfg["core"]["customers_file"]
    return CrmStore(customers_file)

def load_customers_file():
    """Load and return all customer records from the CRM store."""
    store = _get_crm_store()
    return store.load_all()

def save_customers_file(customers):
    """Persist the full customers list to the CRM store."""
    store = _get_crm_store()
    store.save_all(customers)
    logging.debug("The Customer JSON Database file was modified.")

def _pseudonymize_actor(name: str) -> str:
    """Return a short pseudonym for a username for logging."""
    if not name:
        return "actor_unknown"
    salt = os.getenv("LOG_SALT", "")
    short_hash = hashlib.sha256((str(name) + salt).encode()).hexdigest()[:8]
    return f"actor_{short_hash}"

def generate_customer_id(customers):
    """Return next customer identifier (CID) for this year."""
    store = _get_crm_store()
    return store.next_customer_id(customers)


def _find_customer_by_uuid(customers: list, customer_uuid: str):
    """Find a customer by `uuid` in the provided list, or None."""
    for cust in customers:
        if cust.get("uuid") == customer_uuid:
            return cust
    return None


def _clean_form_value(form: dict, field_name: str):
    """Trim and return a form value, or None if empty/missing."""
    raw_value = form.get(field_name)
    if raw_value is None:
        return None
    cleaned = raw_value.strip()
    return cleaned or None


def _update_customer_record(customer: dict, form: dict) -> None:
    """Apply cleaned form values onto an existing customer record in-place."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    customer["first_name"] = _clean_form_value(form, "first_name") or customer.get("first_name")
    customer["last_name"] = _clean_form_value(form, "last_name") or customer.get("last_name")
    customer["preferred_name"] = _clean_form_value(form, "preferred_name") or customer.get("first_name")
    email = _clean_form_value(form, "email")
    customer["email"] = email.lower() if email else customer.get("email")

    customer["phone"] = _clean_form_value(form, "phone") or customer.get("phone")
    customer["country"] = _clean_form_value(form, "country") or customer.get("country")
    customer["timezone"] = _clean_form_value(form, "timezone") or customer.get("timezone") or "UTC"
    customer["status"] = _clean_form_value(form, "status") or customer.get("status")
    customer["preferred_contact"] = _clean_form_value(form, "preferred_contact") or customer.get("preferred_contact")

    # Flags
    customer["vip"] = True if "vip" in form else False
    customer["content_creator"] = True if "content_creator" in form else False
    customer["marketing_opt_in"] = True if "marketing_opt_in" in form else False
    customer["maintenance_notifications"] = True if "maintenance_notifications" in form else False

    # Discord / Minecraft
    discord = customer.setdefault("discord", {})
    discord["username"] = _clean_form_value(form, "discord_username") or discord.get("username")
    minecraft = customer.setdefault("minecraft", {})
    minecraft["username"] = _clean_form_value(form, "minecraft_username") or minecraft.get("username")

    # Audit
    audit = customer.setdefault("audit", {})
    audit["last_modified"] = now
    audit["last_modified_by"] = session.get("technician")
    customer["updated"] = now

# Dashboard Route
@crm_module_bp.route("/", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def crm_dashboard():
    """Render CRM dashboard showing active customers and stats."""
    customers = load_customers_file()
    total_customers = len(customers)
    active_customers_list = [customer for customer in customers if customer.get("status") == "active"]
    vip_customers = sum(1 for customer in customers if customer.get("vip") is True)
    total_lifetime_value = sum(customer.get("lifetime_value", 0) for customer in customers)
    crm_base_stats = {
        "total_customers": total_customers,
        "active_customers": len(active_customers_list),
        "vip_customers": vip_customers,
        "total_lifetime_value": total_lifetime_value
    }
    #return render_template("under_construction.html")
    return render_template("crm/crm_dashboard.html", customers=active_customers_list, loggedInTech=session.get("technician"), stats=crm_base_stats)

# Create New Customer Route
@crm_module_bp.route("/submit-new", methods=["GET", "POST"])
@role_required(ROLE_ITSM_TECH)
def new_customer():
    """Render creation form (GET) and create a new customer (POST)."""
    if request.method == "GET":
        return render_template("crm/submit_new.html")

    form = {key: value for key, value in request.form.items()}

    ok, missing = require_fields(form, ["first_name", "last_name", "email"])
    if not ok or not is_valid_email(form.get("email")):
        return render_template(
            "crm/submit_new.html",
            error="First Name, Last Name, and a valid Email are required."
        ), 400

    customers = load_customers_file()
    submission_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build base record from the form
    base = build_customer_record(form)
    # Enrich with persistence/audit fields
    new_customer_record = {
        "uuid": str(uuid.uuid4()),
        "customer_id": generate_customer_id(customers),
        **base,
        "created": submission_timestamp,
        "created_by": session.get("technician"),
        "audit": {
            "creation_source": "auth_web",
            "last_modified": submission_timestamp,
            "last_modified_by": session.get("technician"),
        },
    }

    initial_note = form.get("crm_worknotes", "").strip()
    if initial_note:
        new_customer_record["crm_worknotes"].append({
            "date": submission_timestamp,
            "created_by": session.get("technician"),
            "note": initial_note,
        })

    customers.append(new_customer_record)
    save_customers_file(customers)
    actor = _pseudonymize_actor(session.get('technician'))
    logging.info("CRM MODULE - Customer %s created actor=%s", new_customer_record['customer_id'], actor)

    return redirect(url_for("crm_module.customer_profile", uuid=new_customer_record["uuid"]))

# View Customer Details Route
@crm_module_bp.route("/profile/<uuid>", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def customer_profile(uuid):
    """Show a single customer's profile by `uuid`."""
    customers = load_customers_file()
    customer = next((cust for cust in customers if cust["uuid"] == uuid), None)
    if not customer:
        return render_template("errors/404.html"), 404
    return render_template("crm/profile.html", customer=customer, loggedInTech=session.get("technician"))


@crm_module_bp.route("/customer/<uuid>/append_note", methods=["POST"])
@role_required(ROLE_ITSM_TECH)
def add_customer_note(uuid):
    """Append a single worknote to a customer record."""
    note_content = (request.form.get("note_content") or "").strip()
    if not note_content:
        return ("", 400)

    customers = load_customers_file()
    found = False
    note_record = {
        "created_by": session.get("technician") or "unknown",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "note": note_content,
    }

    for cust in customers:
        if cust.get("uuid") == uuid:
            cust.setdefault("crm_worknotes", [])
            cust["crm_worknotes"].append(note_record)
            found = True
            break

    if not found:
        return ("Customer not found.", 404)

    save_customers_file(customers)
    return ({"message": "Note added successfully.", "note": note_record}, 200)


@crm_module_bp.route("/customer/<uuid>/edit", methods=["GET", "POST"])
@role_required(ROLE_ITSM_TECH)
def edit_customer(uuid):
    """Render edit form (GET) and apply updates to an existing customer (POST)."""
    customers = load_customers_file()
    customer = _find_customer_by_uuid(customers, uuid)
    if customer is None:
        return render_template("errors/404.html"), 404

    if request.method == "GET":
        return render_template("crm/submit_new.html", customer=customer, loggedInTech=session.get("technician"))

    form = {key: value for key, value in request.form.items()}
    ok, _missing = require_fields(form, ["first_name", "last_name", "email"])
    if not ok or not is_valid_email(form.get("email")):
        return render_template(
            "crm/submit_new.html",
            customer=customer,
            error="First Name, Last Name, and a valid Email are required.",
            loggedInTech=session.get("technician"),
        ), 400

    # Apply updates
    _update_customer_record(customer, form)

    # If an inline worknote was provided, append it
    note_text = (form.get("crm_worknotes") or "").strip()
    if note_text:
        note = {"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "created_by": session.get("technician"), "note": note_text}
        customer.setdefault("crm_worknotes", []).append(note)

    save_customers_file(customers)
    flash(f"Customer {customer.get('customer_id', uuid)} updated.", "success")
    actor = _pseudonymize_actor(session.get('technician'))
    logging.info("CRM MODULE - Customer %s edited actor=%s", customer.get('customer_id'), actor)
    return redirect(url_for("crm_module.customer_profile", uuid=customer["uuid"]))

"""
# Edit Customer Details Route
@crm_module_bp.route("/profile/<uuid>/edit", methods=["POST"])
"""
# Export Customer Data Route
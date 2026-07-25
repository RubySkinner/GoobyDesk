#!/usr/bin/env python3
import logging
import uuid
import hashlib
import os

from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, Response, current_app
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH
from storage.crm_store import CrmStore
from local_handlers.crm_helpers import build_customer_record
from local_handlers.validation import require_fields, is_valid_email

crm_module_bp = Blueprint('crm_module', __name__, url_prefix='/crm')

# NOTE: use @role_required(ROLE_ITSM_TECH) on routes requiring ITSM technicians

def _get_crm_store():
    core_cfg = current_app.config.get("LOADED_CONFIG")
    if core_cfg is None:
        # fallback: try legacy loader
        from local_handlers.local_config_loader import load_core_config
        core_cfg = load_core_config()
    customers_file = core_cfg["core"]["customers_file"]
    return CrmStore(customers_file)

def load_customers_file():
    store = _get_crm_store()
    return store.load_all()

def save_customers_file(customers):
    """Write the given customers back to the customer JSON database.
    Args:
        customers (list[dict]): The full set of customer records to persist.
    """
    store = _get_crm_store()
    store.save_all(customers)
    logging.debug("The Customer JSON Database file was modified.")

def _pseudonymize_actor(name: str) -> str:
    if not name:
        return "actor_unknown"
    salt = os.getenv("LOG_SALT", "")
    h = hashlib.sha256((str(name) + salt).encode()).hexdigest()[:8]
    return f"actor_{h}"

def generate_customer_id(customers):
    """Generate the next sequential CID for the current year.
    Delegates to the store implementation which knows numbering rules.
    """
    store = _get_crm_store()
    return store.next_customer_id(customers)

# Dashboard Route
@crm_module_bp.route("/", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def crm_dashboard():
    # Render the CRM dashboard with a list of customers
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
    if request.method == "GET":
        return render_template("crm/submit_new.html")

    form = {k: v for k, v in request.form.items()}

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
    customers = load_customers_file()
    customer = next((c for c in customers if c["uuid"] == uuid), None)
    if not customer:
        return render_template("errors/404.html"), 404
    return render_template("crm/profile.html", customer=customer, loggedInTech=session.get("technician"))

"""
# Edit Customer Details Route
@crm_module_bp.route("/profile/<uuid>/edit", methods=["POST"])
"""
# Export Customer Data Route
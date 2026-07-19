#!/usr/bin/env python3
import io
import csv
import logging
import uuid

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH
from local_handlers.local_config_loader import load_core_config
from storage.crm_store import CrmStore

core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]
CUSTOMERS_FILE = core_yaml_config["core"]["customers_file"]
SERVICE_APPID_FILE = core_yaml_config["core"]["serviceid_appid_file"]

crm_store = CrmStore(CUSTOMERS_FILE)

logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s",)

crm_module_bp = Blueprint('crm_module', __name__, url_prefix='/crm')

# NOTE: use @role_required(ROLE_ITSM_TECH) on routes requiring ITSM technicians

def load_customers_file():
    return crm_store.load_all()

def save_customers_file(customers):
    """Write the given customers back to the customer JSON database.
    Args:
        customers (list[dict]): The full set of customer records to persist.
    """
    crm_store.save_all(customers)
    logging.debug("The Customer JSON Database file was modified.")

def generate_customer_id(customers):
    """Generate the next sequential CID for the current year.
    Args:
        customers (list[dict]): Existing customer records to scan.
    Returns:
        str: A new customer ID in the form CID-YYYY-NNNN.
    """
    return crm_store.next_customer_id(customers)

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
    return render_template("crm/crm_dashboard.html", customers=active_customers_list, loggedInTech=session["technician"], stats=crm_base_stats)

# Create New Customer Route
@crm_module_bp.route("/submit-new", methods=["GET", "POST"])
@role_required(ROLE_ITSM_TECH)
def new_customer():
    if request.method == "GET":
        return render_template("crm/submit_new.html")

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip()

    if not first_name or not last_name or not email:
        return render_template(
            "crm/submit_new.html",
            error="First Name, Last Name, and Email are required."
        ), 400

    customers = load_customers_file()
    submission_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_customer_record = {
        "uuid": str(uuid.uuid4()),
        "customer_id": generate_customer_id(customers),

        "first_name": first_name,
        "last_name": last_name,
        "preferred_name": request.form.get(
            "preferred_name",
            first_name
        ).strip(),

        "company": request.form.get("company") or None,
        "job_title": request.form.get("job_title") or None,

        "email": email,
        "phone": request.form.get("phone") or None,

        "address": {
            "street": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "country": request.form.get("country") or "US"
        },

        "timezone": request.form.get("timezone") or "UTC",
        "language": "en-US",

        "discord": {
            "username": request.form.get("discord_username") or None,
            "user_id": None
            },

        "minecraft": {
            "username": request.form.get("minecraft_username") or None,
            "uuid": None
        },

        "created": submission_timestamp,
        "created_by": session["technician"],

        "last_seen": None,
        "last_login": None,

        "status": request.form.get("status", "active"),
        "status_reason": None,

        "account_locked": False,
        "email_verified": False,
        "mfa_enabled": False,

        "customer_type": request.form.get(
            "customer_type",
            "individual"
        ),

        "account_tier": request.form.get(
            "account_tier",
            "basic"
        ),

        "vip": "vip" in request.form,
        "content_creator": "content_creator" in request.form,

        "risk_level": "low",

        "lifetime_value": 0.00,

        "billing_currency": "USD",

        "preferred_contact": request.form.get(
            "preferred_contact",
            "email"
        ),

        "marketing_opt_in": "marketing_opt_in" in request.form,

        "maintenance_notifications":
            "maintenance_notifications" in request.form,

        "assigned_account_manager": None,

        "services": [],
        "licenses": [],
        "domains": [],
        "servers": [],

        "support_contract": {
            "enabled": False,
            "sla": None,
            "expires": None
        },

        "custom_fields": {},

        "account_tags": [],

        "crm_worknotes": [],

        "audit": {
            "creation_source": "auth_web",
            "last_modified": submission_timestamp,
            "last_modified_by": session["technician"]
        }
}

    initial_note = request.form.get("crm_worknotes", "").strip()
    if initial_note:
        new_customer_record["crm_worknotes"].append({
            "date": submission_timestamp,
            "created_by": session["technician"],
            "note": initial_note,
        })

    customers.append(new_customer_record)
    save_customers_file(customers)
    logging.info(f"CRM MODULE - Customer {new_customer_record['customer_id']} created by {session['technician']}.")

    return redirect(url_for("crm_module.customer_profile", uuid=new_customer_record["uuid"]))

# View Customer Details Route
@crm_module_bp.route("/profile/<uuid>", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def customer_profile(uuid):
    customers = load_customers_file()
    customer = next((c for c in customers if c["uuid"] == uuid), None)
    if not customer:
        return render_template("errors/404.html"), 404
    return render_template("crm/profile.html", customer=customer, loggedInTech=session["technician"])

"""
# Edit Customer Details Route
@crm_module_bp.route("/profile/<uuid>/edit", methods=["POST"])
@technician_required
"""
# Export Customer Data Route
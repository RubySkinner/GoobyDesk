#!/usr/bin/env python3
import io
import csv
import json
import logging
import uuid

from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, session, Response
from local_handlers.local_config_loader import load_core_config

core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]
CUSTOMERS_FILE = core_yaml_config["core"]["customers_file"]
SERVICE_APPID_FILE = core_yaml_config["core"]["serviceid_appid_file"]

logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s",)

crm_module_bp = Blueprint('crm_module', __name__, url_prefix='/crm')

# Helpers
def technician_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Session-based auth check
        if not session.get("technician"):
            # Unauthorized access attempt
            return render_template("errors/403.html"), 403
        # Authorized technician → proceed to the route
        return func(*args, **kwargs)
    return wrapper

def load_customers_file():
    try:
        with open(CUSTOMERS_FILE, "r") as customer_file:
            return json.load(customer_file)
    except FileNotFoundError:
        logging.critical("Customer JSON Database file could not be located.")
        exit(1)
        return [] # represents an empty list.

def save_customers_file(customers):
    """Write the given customers back to the customer JSON database.
    Args:
        customers (list[dict]): The full set of customer records to persist.
    """
    with open(CUSTOMERS_FILE, "w") as customer_file_write_op:
        json.dump(customers, customer_file_write_op, indent=4)
    logging.debug("The Customer JSON Database file was modified.")

def generate_customer_id(customers):
    """Generate the next sequential CID for the current year.
    Args:
        customers (list[dict]): Existing customer records to scan.
    Returns:
        str: A new customer ID in the form CID-YYYY-NNNN.
    """
    current_year = datetime.now(timezone.utc).year
    year_prefix = f"CID-{current_year}-"
    existing_ids = [c.get("customer_id", "") for c in customers if c.get("customer_id", "").startswith(year_prefix)]
    next_sequence = len(existing_ids) + 1
    return f"{year_prefix}{next_sequence:04d}"

# Dashboard Route
@crm_module_bp.route("/", methods=["GET"])
@technician_required
def crm_dashboard():
    # Render the CRM dashboard with a list of customers
    try:
        with open(CUSTOMERS_FILE, "r") as customers_file:
            customers = json.load(customers_file)
    except FileNotFoundError:
        logging.critical("Customer JSON Database file could not be located.")
        exit(1)
        return []  # represents an empty list.
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
@technician_required
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
    submission_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_customer_record = {
        "uuid": str(uuid.uuid4()),
        "customer_id": generate_customer_id(customers),
        "first_name": first_name,
        "last_name": last_name,
        "preferred_name": request.form.get("preferred_name", "").strip() or first_name,

        "company": request.form.get("company", "").strip() or None,
        "email": email,
        "phone": request.form.get("phone", "").strip() or None,

        "discord_username": request.form.get("discord_username", "").strip() or None,
        "discord_user_id": None,
        "minecraft_username": request.form.get("minecraft_username", "").strip() or None,

        "country": request.form.get("country", "").strip() or None,
        "timezone": request.form.get("timezone", "").strip() or None,
        "created": submission_timestamp,
        "last_seen": None,
        "last_login": None,

        "status": request.form.get("status", "active"),
        "status_reason": None,
        "account_locked": False,
        "email_verified": False,
        "mfa_enabled": False,

        "vip": request.form.get("vip") == "on",
        "content_creator": request.form.get("content_creator") == "on",

        "risk_level": "low",
        "lifetime_value": 0.00,
        "billing_currency": "USD",
        "last_order": None,
        "last_payment": None,

        "preferred_contact": request.form.get("preferred_contact", "email"),
        "marketing_opt_in": request.form.get("marketing_opt_in") == "on",
        "maintenance_notifications": request.form.get("maintenance_notifications") == "on",
        "assigned_account_manager": None,
        "services": [],

        "account_tags": [],

        "notes": [],
    }

    initial_note = request.form.get("notes", "").strip()
    if initial_note:
        new_customer_record["notes"].append({
            "date": submission_timestamp,
            "author": session["technician"],
            "note": initial_note,
        })

    customers.append(new_customer_record)
    save_customers_file(customers)
    logging.info(f"CRM MODULE - Customer {new_customer_record['customer_id']} created by {session['technician']}.")

    return redirect(url_for("crm_module.customer_profile", uuid=new_customer_record["uuid"]))

# View Customer Details Route
@crm_module_bp.route("/profile/<uuid>", methods=["GET"])
@technician_required
def customer_profile(uuid):
    customers = load_customers_file()
    customer = next((c for c in customers if c["uuid"] == uuid), None)
    if not customer:
        return render_template("errors/404.html"), 404
    return render_template("crm/customer_profile.html", customer=customer, loggedInTech=session["technician"])

"""
# Edit Customer Details Route
@crm_module_bp.route("/profile/<uuid>/edit", methods=["POST"])
@technician_required
"""
# Export Customer Data Route
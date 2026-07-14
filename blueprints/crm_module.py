#!/usr/bin/env python3
import io
import csv
import json
import logging
from functools import wraps
from flask import Blueprint, render_template, session, Response
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
        logging.critical("Ticket JSON Database file could not be located.")
        exit(1)
        return [] # represents an empty list.

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
    active_customers = sum(1 for customer in customers if customer.get("status") == "active")
    vip_customers = sum(1 for customer in customers if customer.get("vip") is True)
    total_lifetime_value = sum(customer.get("lifetime_value", 0) for customer in customers)


    return render_template("crm/crm_dashboard.html", customers=customers, loggedInTech=session["technician"])

# Create New Customer Route
@crm_module_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def new_customer():
    return render_template("crm/submit_new.html")

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
#!/usr/bin/env python3
import logging
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH

from local_handlers.local_config_loader import load_core_config
from storage.service_appid_store import ServiceAppIdStore

core_yaml_config = load_core_config()
LOG_LEVEL = core_yaml_config["logging"]["level"]
LOG_FILE = core_yaml_config["logging"]["file"]

service_appid_store = ServiceAppIdStore.from_config()

logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(levelname)s - %(message)s",)

serviceid_module_bp = Blueprint("serviceid_module", __name__, url_prefix="/serviceid")

# use @role_required(ROLE_ITSM_TECH)

def load_service_appids():
    return service_appid_store.load_all()

@serviceid_module_bp.route("/", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def serviceid_dashboard():
    services = load_service_appids()
    return render_template("services-appid/dashboard.html", services=services, loggedInTech=session.get("technician"),)

@serviceid_module_bp.route("/submit-new", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def services_appid_dashboard():
    return redirect(url_for("under_construction"))

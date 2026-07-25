#!/usr/bin/env python3
import logging
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for
from local_handlers.auth_decorators import role_required, ROLE_ITSM_TECH

from flask import current_app
from local_handlers.local_config_loader import load_core_config
from storage.service_appid_store import ServiceAppIdStore

def _get_config():
    cfg = current_app.config.get("LOADED_CONFIG")
    if cfg is None:
        cfg = load_core_config()
    return cfg

def _get_service_appid_store():
    cfg = _get_config()
    return ServiceAppIdStore(cfg["core"]["serviceid_appid_file"])

serviceid_module_bp = Blueprint("serviceid_module", __name__, url_prefix="/serviceid")

# use @role_required(ROLE_ITSM_TECH)
def load_service_appids():
    store = _get_service_appid_store()
    return store.load_all()

@serviceid_module_bp.route("/", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def serviceid_dashboard():
    services = load_service_appids()
    return render_template("services-appid/dashboard.html", services=services, loggedInTech=session.get("technician"),)

@serviceid_module_bp.route("/submit-new", methods=["GET"])
@role_required(ROLE_ITSM_TECH)
def services_appid_dashboard():
    return redirect(url_for("under_construction"))

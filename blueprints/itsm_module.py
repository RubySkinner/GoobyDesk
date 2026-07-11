#!/usr/bin/env python3
import json
import logging

from datetime import datetime
from flask import Blueprint, request, jsonify

import local_handlers.local_webhook_handler as local_webhook_handler
from local_handlers.local_config_loader import load_core_config

logging.basicConfig(filename=LOG_FILE,level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),format="%(asctime)s - %(levelname)s - %(message)s")
""" Above is the default logging configuration.
Debug - Detailed information
Info - Successes
Warning - Unexpected events
Error - Function failures
Critical - Serious application failures
"""
itsm_module_bp = Blueprint('itsm', __name__, url_prefix='/itsm')

@itsm_module_bp.route("/", methods=["GET"])
def itsm_home():
    return jsonify({"message": "Welcome to the ITSM Module!"}), 200
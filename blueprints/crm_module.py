#!/usr/bin/env python3
import io
import csv
import json
import logging
from functools import wraps
from flask import Blueprint, render_template, session, Response
from local_handlers.local_config_loader import load_core_config

crm_module_bp = Blueprint('crm_module', __name__, url_prefix='/crm')

# Dashboard Route

# Create New Customer Route

# View Customer Details Route

# Edit Customer Details Route

# Export Customer Data Route

#!/usr/bin/env python3
import io
import csv
import json
import logging
from functools import wraps
from flask import Blueprint, render_template, session, Response
from local_handlers.local_config_loader import load_core_config

hr_module_bp = Blueprint('hr_module', __name__, url_prefix='/hr')

# Dashboard Route

# Create New Employee Route

# View Employee Details Route

# Edit Employee Details Route

# Export Employee Data Route

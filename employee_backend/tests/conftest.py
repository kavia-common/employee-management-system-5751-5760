"""
Pytest configuration to ensure 'src' package is importable during test collection.

This adjusts sys.path so that 'from src.api.main import app' works regardless of
how pytest sets the working directory.
"""
from __future__ import annotations

import os
import sys

# Compute the backend project root (the directory containing 'src' and 'tests')
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Prepend backend root to sys.path if not already present
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

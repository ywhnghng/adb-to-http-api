"""Pytest configuration.

Ensures the project root (which contains the ``app`` and ``gui`` packages) is
importable from the test modules regardless of how pytest discovers tests.
"""

from __future__ import annotations

import os
import sys

# Insert the project root directory (the parent of this conftest.py) at the
# front of sys.path so that ``import app`` / ``import gui`` resolve.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

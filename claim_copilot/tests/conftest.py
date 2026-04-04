"""
conftest.py — Shared pytest configuration and fixtures for the ClaimCopilot test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (parent of claim_copilot/) is on sys.path
# so that `import claim_copilot.xxx` works from any test file.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

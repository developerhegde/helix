"""Runtime configuration, read at call time and never at import (LLD 01 §3.3)."""

from __future__ import annotations

import os
from typing import Optional

from . import product_identity as pid


def client_profile_from_env() -> Optional[str]:
    """The profile path named by the environment, if any. No other lookup is made."""
    return os.environ.get(pid.PROFILE_ENV_VAR) or None

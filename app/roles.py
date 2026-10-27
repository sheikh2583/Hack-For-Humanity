"""Staff sign-in and role helpers for the Inspector Portal (module S1).

Input schema: the typed passcode and display name, and the session state. Output schema:
the role string ``"public"`` (default) or ``"inspector"``. One shared staff passcode is read
from ``st.secrets["staff_passcode"]`` (or ``DHOA_STAFF_PASSCODE``) and takes precedence.
When no staff passcode exists, the portal offers the built-in ``dhoa-demo`` passcode as a
demo login. ``demo_mode = false`` (or ``DHOA_DEMO_MODE=0``) disables that fallback.
"""

from __future__ import annotations

import hmac
import os
from collections.abc import MutableMapping
from typing import Any

PUBLIC = "public"
INSPECTOR = "inspector"
ROLE_KEY = "dhoa_role"
NAME_KEY = "dhoa_staff_name"
DEMO_NAME = "Demo"
DEMO_PASSCODE = "dhoa-demo"
_MAX_NAME = 60


def _secret(name: str) -> Any:
    """Read ``name`` from Streamlit secrets; ``None`` when secrets are not configured."""
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:  # no secrets file, or running outside Streamlit
        return None


def configured_passcode() -> str:
    """Return the configured staff passcode, or the enabled demo passcode."""
    value = _secret("staff_passcode") or os.environ.get("DHOA_STAFF_PASSCODE") or ""
    if value:
        return str(value)
    return DEMO_PASSCODE if demo_enabled() else ""


def demo_enabled() -> bool:
    """Whether demo sign-in is enabled (defaults on only when no staff passcode exists)."""
    value = _secret("demo_mode")
    if value is None:
        value = os.environ.get("DHOA_DEMO_MODE")
    if value is None:
        has_staff_passcode = bool(
            _secret("staff_passcode") or os.environ.get("DHOA_STAFF_PASSCODE")
        )
        return not has_staff_passcode
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def signin_available() -> bool:
    """Whether staff sign-in is available (requires a configured passcode)."""
    return bool(configured_passcode())


def passcode_matches(supplied: str, expected: str) -> bool:
    """Constant-time passcode comparison; an empty expected passcode never matches."""
    if not expected or not supplied:
        return False
    return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))


def clean_name(name: str | None) -> str:
    """Trim and shorten a display name; blank becomes ``"Staff"``."""
    text = " ".join(str(name or "").split())[:_MAX_NAME]
    return text or "Staff"


def _state(state: MutableMapping | None) -> MutableMapping:
    if state is not None:
        return state
    import streamlit as st

    return st.session_state


def get_role(state: MutableMapping | None = None) -> str:
    """Current role: ``"inspector"`` only after a successful sign-in, else ``"public"``."""
    return INSPECTOR if _state(state).get(ROLE_KEY) == INSPECTOR else PUBLIC


def is_staff(state: MutableMapping | None = None) -> bool:
    """True when the session is signed in as staff."""
    return get_role(state) == INSPECTOR


def staff_name(state: MutableMapping | None = None) -> str:
    """Display name of the signed-in staff member ("" when public)."""
    return str(_state(state).get(NAME_KEY, "")) if is_staff(state) else ""


def sign_in(passcode: str, name: str | None, state: MutableMapping | None = None) -> bool:
    """Sign in with the shared passcode; return whether it was accepted."""
    if not passcode_matches(passcode or "", configured_passcode()):
        return False
    session = _state(state)
    session[ROLE_KEY] = INSPECTOR
    session[NAME_KEY] = clean_name(name)
    return True


def sign_out(state: MutableMapping | None = None) -> None:
    """Return the session to the public role."""
    session = _state(state)
    session.pop(ROLE_KEY, None)
    session.pop(NAME_KEY, None)

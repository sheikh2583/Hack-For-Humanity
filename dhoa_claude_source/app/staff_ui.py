"""Header control for staff sign-in (R1). Shown only when a passcode or demo mode is configured.

Public visitors on a deployment without staff secrets never see it, so nothing hints at
a restricted area. Texts come from ``strings`` in both languages.
"""

from __future__ import annotations

import streamlit as st

try:
    from app import roles
    from app import strings as T
except ImportError:  # app dir on sys.path
    import roles
    import strings as T


def _role_label(role: str) -> str:
    return {roles.PUBLIC: T.ROLE_PUBLIC, roles.INSPECTOR: T.ROLE_INSPECTOR, roles.ADMIN: T.ROLE_ADMIN}[role]


def available() -> bool:
    """Whether the staff control should be drawn at all."""
    return roles.staff_sign_in_enabled() or roles.demo_mode() or roles.is_staff()


def _submit() -> None:
    """Form callback: try the typed passcode."""
    st.session_state["dhoa_signin_failed"] = (
        roles.sign_in(st.session_state.get("dhoa_signin_code", ""), st.session_state.get("dhoa_signin_name", "")) is None
    )
    st.session_state["dhoa_signin_code"] = ""


def _demo_changed() -> None:
    roles.demo_as(st.session_state.get("dhoa_demo_role", roles.PUBLIC))


def _sign_out() -> None:
    roles.sign_out()
    st.session_state["dhoa_demo_role"] = roles.PUBLIC


def render_staff_control() -> None:
    """Draw the sign-in popover (public) or the role chip with sign-out (staff)."""
    if not available():
        return
    role = roles.get_role()
    if role == roles.PUBLIC:
        label, icon = T.STAFF_SHORT, ":material/lock:"
    else:
        label, icon = _role_label(role), ":material/verified_user:"
    with st.container(key="dhoa_staff_control"):
        with st.popover(label, icon=icon, width="stretch"):
            if role == roles.PUBLIC and roles.staff_sign_in_enabled():
                st.markdown(f"**{T.STAFF_SIGN_IN}**")
            if role != roles.PUBLIC:
                name = roles.staff_name()
                st.markdown(T.STAFF_SIGNED_IN_FMT.format(f"{_role_label(role)}" + (f" · {name}" if name else "")))
                st.button(T.STAFF_SIGN_OUT, key="dhoa_signout", on_click=_sign_out, width="stretch")
            elif roles.staff_sign_in_enabled():
                with st.form("dhoa_signin_form", border=False):
                    st.text_input(T.STAFF_YOUR_NAME, key="dhoa_signin_name", max_chars=roles.MAX_NAME_LENGTH)
                    st.text_input(T.STAFF_PASSCODE, key="dhoa_signin_code", type="password")
                    st.form_submit_button(T.STAFF_SIGN_IN_BUTTON, on_click=_submit, width="stretch")
                if roles.attempts_left() == 0:
                    st.error(T.STAFF_LOCKED)
                elif st.session_state.get("dhoa_signin_failed"):
                    st.error(T.STAFF_WRONG_PASSCODE)
            if roles.demo_mode():
                st.selectbox(
                    T.DEMO_AS, list(roles.ROLES), format_func=_role_label,
                    key="dhoa_demo_role", on_change=_demo_changed,
                )

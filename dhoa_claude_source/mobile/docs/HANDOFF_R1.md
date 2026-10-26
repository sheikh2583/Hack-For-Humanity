# HANDOFF R1 — Role layer and staff sign-in

## Changes
- `app/roles.py` (new): `get_role()`, `is_staff()`, `require(role)`, `staff_name()`, `sign_in(passcode, name)`, `sign_out()`, `demo_as(role)`, `staff_sign_in_enabled()`, `demo_mode()`. Roles: public (default), inspector, admin (admin may do everything inspector may).
- Passcodes come from secrets `staff_passcode_inspector` / `staff_passcode_admin` (or env `DHOA_STAFF_PASSCODE_INSPECTOR` / `_ADMIN`). Compared with `hmac.compare_digest`; never stored in session state or logged. Admin is checked first. 5 wrong tries lock the session (reload to retry). Empty/unset passcode = disabled.
- `demo_mode` secret (or `DHOA_DEMO_MODE=1`) adds a "Demo as" selector inside the Staff menu. Off by default.
- `app/staff_ui.py` (new): header control. Public: a "Staff" popover with name + passcode form. Signed in: role chip (Inspector/Admin) with "Sign out". Not drawn at all when no passcode and no demo mode are configured, so a deployment without secrets looks exactly as before.
- `app/streamlit_app.py`: `render_header` uses a 5th narrow column for the control only when it is available (4 columns as before otherwise); `import staff_ui`.
- `app/styles.py`: staff control stays on one line; on phones it wraps to its own row.
- Strings (both catalogues): STAFF_SIGN_IN, STAFF_SHORT, STAFF_PASSCODE, STAFF_YOUR_NAME, STAFF_SIGN_IN_BUTTON, STAFF_WRONG_PASSCODE, STAFF_LOCKED, STAFF_SIGN_OUT, STAFF_SIGNED_IN_FMT, ROLE_PUBLIC, ROLE_INSPECTOR, ROLE_ADMIN, DEMO_AS (Bangla wording needs native review).
- `.streamlit/secrets.toml.example` (new). Real `.streamlit/secrets.toml` untouched.
- Tests: `tests/test_roles_r1.py` (10 tests); `tests/test_layout_m11.py` header test updated for the new column list.

## How to verify
1. `pytest tests/test_roles_r1.py tests/test_layout_m11.py`
2. Run with `DHOA_STAFF_PASSCODE_INSPECTOR=a DHOA_STAFF_PASSCODE_ADMIN=b DHOA_DEMO_MODE=1 streamlit run app/streamlit_app.py`: header shows "Staff"; wrong code -> error; right code -> chip "Inspector"/"Admin"; Sign out -> back to "Staff"; demo selector switches role.
3. Run with no env vars: no Staff control anywhere.

## Decisions
- No identity provider yet; one passcode per role plus a name typed at sign-in (used later for notes/status). Everything asks `roles.get_role()`, so Google sign-in can replace the passcode check later in this one module.
- Nothing is gated yet (that is R4+). R1 only establishes the role.

## Toggle bugs noticed
- Language radio renders as a vertical stacked pill at 1280 px with the sidebar open (also without my change). Left for Module L.

## NOT verified
- Real deployment on Streamlit Cloud with secrets set in its Secrets panel.
- Phone layout: control wraps to its own full-width row (works, not side by side with "How to use"; a CSS attempt to share the row did not take effect and was removed).
- Full suite: 15 failures exist before and after (deploy_m9 x3, infer, language_switch x2, osm_layers x4, voice_p10 x4, plus tests/test_inspect_raster.py collection error); R1 adds none.

## Owner hand-checks
- Set the two passcodes in Streamlit Cloud Secrets before the demo; change them afterwards.
- Review Bangla strings.

## First step for next module (R2)
Rename user-facing "Inspector view"/"Community view" text (VIEW_*, HELP_*, voice scripts VOICE_INSPECTOR_SCRIPT/VOICE_COMMUNITY_SCRIPT, docs/DASHBOARD_GUIDE.md). Note: tests/test_voice_p10.py and strings tests may pin some of that text.

# HANDOFF S1 — Four sections, roles, Inspector Portal sign-in

## Changes
- app/roles.py (new): get_role/is_staff/sign_in/sign_out/staff_name, one shared passcode from st.secrets["staff_passcode"] or env DHOA_STAFF_PASSCODE (constant-time compare, never logged). Optional demo sign-in: secret demo_mode=true or env DHOA_DEMO_MODE=1. No passcode configured -> sign-in disabled, everyone public.
- Top bar is now exactly: Overview · Kilns near me · 🔒 Inspector Portal · About (hero.VIEW_MODES order changed; internal values overview/community/inspector/about kept).
- Inspector Portal: public sees an in-page sign-in (passcode + name). Staff see a second, smaller row: Dashboard · Map · Work · Reports (+ "Signed in: name", Sign out). Map = the previous map view unchanged (sidebar filters only on this tab). Dashboard = headline numbers + the overview charts. Work and Reports show a "Coming soon" card (S4/S5). Reports label shows a count badge via _open_report_count() (returns 0 until S4).
- Public can no longer reach the staff map: Overview shows only "Find kilns near me" to public (staff also get the map button); district links on the Overview open Kilns near me for public and the filtered Portal map for staff.
- Sign out -> Overview, portal row removed.
- Wording: NAV_NEAR_ME, VIEW_*, HELP_* texts renamed in both catalogues; 21 new PORTAL_*/NAV_INSPECTOR strings in both.
- Header column widths changed to fit the longer labels.
- app/styles.py: portal bar and sign-in styling (tokens only, dark theme); mobile wrapping of the four sections and portal tabs.
- Tests: new tests/test_roles_s1.py (10); tests that open the staff map now set dhoa_role; hero order test and hero-CTA/overview-link tests updated.

## How to verify
Set secret staff_passcode (or DHOA_STAFF_PASSCODE=xyz), run the app, click 🔒 Inspector Portal, sign in, switch tabs, sign out. pytest tests/test_roles_s1.py.

## Decisions
One passcode, one staff role (no admin). Role lives in session state only. docs/DASHBOARD_GUIDE.md and README still describe old "Inspector/Community view" wording: NOT edited (do in S2/S7 wording pass). Voice scripts (voice_scripts / strings VOICE_*) still say "Inspector view"/"Welcome to Dhoa": left to the owner (audio is pre-recorded).

## Toggle bugs noticed
None new.

## NOT verified
- Desktop 1280 px (en + bn): sign-in, wrong passcode, portal tabs, sign out all verified. At 400 px the four sections and the portal tabs now wrap into 2x2 (verified by screenshot). NOT re-checked after the very last CSS line (portal bar forced to row layout so "Signed in: name" and the Sign out button sit side by side instead of a narrow stack): look at 400/484 px.
- Help popover label is truncated in Bangla ("কীভা...") at 1280 px: widen or shorten the label.
- Full suite: remaining failures equal the baseline (rasterio missing, osm/deploy/infer/voice-audio/language tests).
- Sign-in with real st.secrets on a deployment.

## Owner hand-checks
Bangla wording of the new strings. Sidebar is expanded on phones at first load (initial_sidebar_state="expanded", pre-existing) and covers the page for public users; consider "auto".

## First step for next module (S2)
Add kiln_data.public_view() stripping staff-only columns, simplify the public Overview (no High count, no High series, no type split) and move those into Inspector > Dashboard (currently Dashboard = old overview charts).

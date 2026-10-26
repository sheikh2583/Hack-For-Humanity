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


## Follow-up (after S1): portal bar CSS and Bangla help label
Changes (CSS and one string only; nothing else touched):
- app/styles.py, portal bar block (phones, max-width 768 px): the "Signed in: name" column now takes the free width (`flex: 1 1 0`, wraps long names with `overflow-wrap: anywhere`) and the Sign out column is `flex: 0 0 auto` with a 7.5 rem minimum and `white-space: nowrap`, so the two sit side by side and the label is never cut. The segmented control no longer clips (`overflow: visible`), so the portal tabs keep wrapping 2x2. The percentage widths (50% / 35%) are gone.
- app/strings_bn.py: `HOW_TO_USE` "কীভাবে ব্যবহার করবেন?" -> "সহায়তা" (Help). The header columns (and so the four sections) were not resized. English "How to use" is unchanged.

NOT verified (follow-up): the browser check at 1280 / 484 / 400 px in Bangla and English was NOT done. PyPI was blocked in the authoring session, so Streamlit, Playwright's target app and pytest could not run. Both edits are reasoned from the CSS and are unseen in a browser. Please check, signed in on the Map tab with the sidebar closed: (1) at 400 and 484 px the four sections and the portal tabs show in full (2x2 is fine); (2) "Signed in: name" and Sign out are on one line without truncation; (3) at 1280 px in Bangla the help button reads "সহায়তা" in full and the four sections are not clipped.

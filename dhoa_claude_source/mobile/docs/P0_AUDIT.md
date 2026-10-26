# P0 — Baseline and design audit

Screenshots: `docs/screens/p0/` (Inspector at 1280/768/360, Community at 1280/768; made by
`scripts/shoot_screens.py`). Tiles are blocked in the sandbox, so basemaps are blank grey.
The empty state and the PDFs were **not** captured (see HANDOFF.md).

## Baseline health
- Dashboard tests: 313 pass. 8 fail, none in dashboard code: 3 in `test_deploy_m9.py`
  (`.github/workflows/keep_warm.yml` and `docs/DEMO_SCRIPT.md` are missing from the zip),
  `test_infer.py` and `test_osm_layers.py` (pipeline, out of scope).
- **Blocker found and fixed:** the Inspector did not load at all (red "ড্যাশবোর্ড দেখানো যায়নি").
  Cause: the English-toggle work put `on_change` callbacks on widgets inside the filter
  `st.form`, which Streamlit forbids. Fixed in `app/streamlit_app.py` (`_pull_form_values`).
- Benchmark (2,135 rows): load 0.43 s, filter 0.005 s, list frame 0.09 s, marker payload 0.02 s,
  community search 10 km 0.008 s, map payload+build 0.06 s, map HTML 0.18 MB. All inside the targets.

## The 10 worst visual / UX issues (seen in the screenshots)
1. **Mobile first screen is the filter drawer.** At 360 px the sidebar opens full-screen, so a
   first-time visitor sees filters, not content. (P8/P2)
2. **No hero, no purpose, no next step.** The top is a title, a language radio, a view switch
   labelled "ভিউ বাছাই করুন" and a popover. (P2)
3. **Two metric rows say nearly the same thing** (header: 2,135 / 430; summary strip: 2,135 / 430 ...)
   and use different labels ("মোট ভাটা" vs "মেলা প্রার্থী"). (P2/P4)
4. **The hotline appears twice** (sidebar and footer) and the number is still unverified. (P7)
5. **Help button shows two icons** ("(?) ? কীভাবে ব্যবহার করবেন?"). (P1)
6. **Mixed scripts:** area names are English inside Bangla text ("Savar, ঢাকা",
   "যেমন: Savar"). Data holds English names; needs a decision. (P1/P5)
7. **Tiny low-contrast grey captions** stacked above the map (marker legend, PDF hint) read as noise;
   no real legend. (P1/P4)
8. **Map area is a blank dark box while loading** (no loading message or skeleton). (P7)
9. **Community step 1 contains an empty grey bar** between the picker and the "not in the list?"
   expander, and the whole page is one long column. (P5)
10. **Priority colours are red / orange / green** (red-green is the classic colour-blind clash);
    shapes help, but the palette should be Okabe-Ito-safe. (P1)

Also known: the English toggle is buggy (owner will fix later; not touched).

## Plan
P1 tokens + CSS (fixes 5, 7, 10) -> P2 hero + top navigation (1, 2, 3, 4) -> P3 overview ->
P4 inspector -> P5 near me (9, 6) -> P6 PDFs -> P7 states (8) -> P8 mobile/a11y -> P9 demo kit.

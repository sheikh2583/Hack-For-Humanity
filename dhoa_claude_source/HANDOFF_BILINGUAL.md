# HANDOFF: English + Bangla toggle (work in progress, NOT yet run end to end)

Extract over the project root (changed files only).

## What was done
- app/strings.py is now a language-aware entry point. `T.NAME` returns the text for the active
  language (st.session_state["dhoa_lang"], "bn" default, `?lang=en` supported). Catalogues:
  app/strings_bn.py (the old strings.py, unchanged text) and app/strings_en.py (NEW, all 213 names,
  same {format} fields). Helpers: T.get_language/set_language/text/variants, T.LazyMapping/LazySequence.
- Import-time constants that froze one language are now lazy (streamlit_app.py: KILN_TYPE_LABELS,
  INSPECTOR/COMMUNITY_CSV_COLUMNS, METRIC_LABELS, _GPS_ERRORS; kiln_data.py: priority/district/feature
  label maps, _POPUP_RULES).
- Language is part of cache keys: _prepared_data(..., lang) and the data version string carry the
  language, so every cache keyed by version (marker payload, list payload, CSV, places) is per-language;
  _cached_community_pdf got a lang argument.
- Priority multiselect now stores canonical "High/Medium/Low" (labels translated by format_func), so the
  selection survives a language switch.
- Header: language radio (বাংলা / English) next to the title (_render_language_toggle), URL ?lang= kept in sync.
- New tests/test_strings_i18n.py (same names, same format fields, no Bangla in English except brand).
- Test hygiene: fixed test_app_startup (caplog), test_community_m5 (reads strings_bn.py), skipped 2 dead
  popup tests, started repairing tests/test_dashboard_presentation.py.

## NEXT AGENT: do these first
1. Run `pytest -q` (install typer, rich first). test_dashboard_presentation.py is only partly repaired:
   it still imports removed names and ~11 tests target APIs removed in M2-M7. Mark them
   `@pytest.mark.skip(reason="obsolete ...")` or rewrite. In the new area-name test, also patch the module
   the app imports: `import strings as app_strings; monkeypatch.setattr(app_strings, "get_language", lambda: "en")`
   (app.strings and strings are two module objects).
2. Verify in a real browser (Playwright; sandbox blocks CDNs, serve Leaflet/jQuery/Bootstrap locally via
   route interception): toggle language on Inspector and Community; check no JS errors, map iframe stays
   580px, selection and filters survive the switch, priority filter keeps its selection.
   Known/expected: switching language rebuilds the map once (tooltip text is inside the map script), so the
   view re-fits; confirm it does not blank.
3. Check every T.* use in cached functions and widget labels for stale-language bugs (search for text built
   at import time or stored in st.session_state).
4. English copy needs native review. PDFs: community PDF is mostly English already; the per-kiln PDF
   (src/eval/generate_report.py) language is untouched. Restore src/eval/fonts/NotoSansBengali-Regular.ttf
   and static/ fonts from GitHub (not in the zip).
5. Then continue the pitch phase: P1 design system, P2 hero, P3 overview/district chart, P4-P9.
   Keep rules: no cached folium.Map objects, returned_objects=["last_object_clicked"], no invented data.

## NOT verified
Nothing in this zip was run in a browser; only py_compile and the tests listed above (before the last edit).

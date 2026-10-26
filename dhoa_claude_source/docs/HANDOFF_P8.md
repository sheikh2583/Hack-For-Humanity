# HANDOFF P8 - Mobile and accessibility (PARTIAL: static checks only)

## What changed
- `app/components/priority_candidate_list/index.html`: region role + tabindex on the scroller with a localised label, `scope="col"`, localised per-row button names, `document.documentElement.lang`, hidden duplicate scrollbar, white focus rings, removed hard-coded English row aria-label. New component args from Python: `aria_label`, `aria_select_fmt`, `lang`.
- `app/styles.py`: 44 px footer links, overflow-wrap rules, scrollable wide tables, media max-width, shimmer off for reduced motion.
- `tools/check_widths.py` (new): Playwright run at 360/412/768/1280; checks horizontal overflow, targets under 44 px, focus ring, optional axe-core (`--axe path/to/axe.min.js`); screenshots to `screens_p8/`; exit 1 on failure.
- `tests/test_a11y_p8.py`.

## How to verify
`streamlit run app/streamlit_app.py`, then `python tools/check_widths.py http://localhost:8501 --nav "<Overview>,<Map>,<Near me>,<About>" --axe axe.min.js` once per language (use the visible nav labels). Fix anything it prints.

## Not done / not verified
- NOT RUN in a browser: no Chromium here, so the "Playwright passes at all widths" and "axe/Lighthouse no critical issues" criteria are OPEN. This module is not finished until you run the script.
- The page `<html lang>` cannot be set from Streamlit; only the candidate-list iframe gets it.
- No skip link (Streamlit gives no stable anchor); keyboard order of Streamlit's own widgets not audited.
- Map (Leaflet) keyboard use and marker labels not audited.

## Toggle bugs noticed
None new.

## Owner hand-checks
Tab through the list with a keyboard; try a screen reader (TalkBack/VoiceOver) on the list; check the map height and one-handed use on a real phone.

## First step for next agent
Run `tools/check_widths.py` in both languages, fix reported overflow/target failures, then proceed to P9.

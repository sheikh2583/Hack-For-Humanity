# HANDOFF P6 - Kiln detail and PDF reports (DONE, two items still to verify by hand)

## What changed
- `src/eval/pdf_kit.py` (new, earlier): bilingual `LABELS`, mixed-script font runs (Noto Sans Bengali + HarfBuzz for Bangla, Helvetica for Latin), wrap/fit helpers, header band, footer with page x/y.
- `src/eval/generate_report.py`: `generate_kiln_report(row, lang="bn")` rewritten (earlier).
- `src/eval/generate_community_report.py` (new): `generate_community_report(location, rows, radius_m, lang)`. Two-pass layout so every page shows "Page x / y"; table header repeats on each page; "What you can do" block moves to a new page if it does not fit.
- `app/streamlit_app.py`: `community_alert_pdf(location, rows, radius_m, lang=None)` delegates to the new module (language defaults to the active one; language is already in the cache key of `_cached_community_pdf`). `_PDF_COLUMNS` gained `upazila`, `district`. The signature seen by `tests/test_dashboard_m2.py` is unchanged.
- `app/styles.py`: main-block padding-top 4.25rem so the fixed Streamlit bar does not cover the language toggle.
- `tests/test_pdf_p6.py` (new), `CHANGELOG.md` entry.

## Decisions
- PDFs follow the active language. Footer advisory text removed (AGENTS.md rule 8).
- Upazila names are English in the data, so they stay English inside the Bangla PDF.
- No QR code (fpdf2 has none); clickable links instead.

## Verify
`pytest tests/test_pdf_p6.py tests/test_generate_report.py tests/test_dashboard_m2.py tests/test_strings_i18n.py` -> 30 passed, 1 skipped (needs real parquet). Rendered 60-row community PDFs (3 pages) in bn and en with pdftoppm and checked page 1 (bn) and the last page (en).

## New strings
`pdf_kit.LABELS` (bn, en; keys incl. `near_in`, `in_area`, `col_*`, `can_do`, `do_1..4`, `community_note`). No `strings_*.py` change. Needs native-speaker review.

## Toggle bugs noticed
None new.

## NOT verified
- Toggle visibility at 4.25rem padding in a real browser (1280/484/360 px).
- Full pytest suite and Playwright checks (no real parquet or Chromium in this sandbox).
- PDF viewers other than poppler (Acrobat, phone viewers): Bangla conjuncts.
- Community PDF with real long names from the parquet.

## Owner hand-checks
- Bangla wording in `LABELS`, especially `near_in`/`in_area` grammar.
- Hotline 16131 in `do_1` is still unverified (P7 gates it behind a config flag).
- Keep `src/eval/fonts/NotoSansBengali-Regular.ttf` in the repo.
- Download both PDFs from the running app in both languages and open them on a phone.

## First step for next agent (P7)
Read `docs/HANDOFF_P6.md` and `AGENTS.md`, run `pytest`, then in `app/streamlit_app.py` find the existing loading/empty/error helpers (M4) and list which screens still lack one; add the hotline config key + flag in `config/dashboard.yaml` and make the PDF `do_1` line and any UI hotline link respect it.

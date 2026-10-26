# M6 — Header and wording: handoff

## CHANGELOG (M6)
- **Data date**: the header's "last updated" metric now shows the loaded data file's modification date (`_data_date_label`), not `datetime.now`. The duplicate date in the subtitle (`SUBTITLE_UPDATED_FMT`) was removed. Label: "তথ্য হালনাগাদের তারিখ".
- **Advisory wording**: "পরিবেশ বিপজ্জনক ভাটা" -> "উচ্চ অগ্রাধিকার প্রার্থী"; "আইন লঙ্ঘন" -> "নিয়মের সংকেত"; CSV column "লঙ্ঘন সংখ্যা" -> "নিয়মের সংকেতের সংখ্যা".
- **Law expander removed** from the UI, and `LAW_TEXT` / `RELEVANT_LAW_…` deleted from `strings.py`. It hard-coded legal distances (1 km, 2 km, 0.5 km) outside `config/rules.yaml` (AGENTS rules 2 and 8). I chose removal over sourcing from config because the text also quotes Act sections that are not in rules.yaml. The wording stays in `docs/legal_basis.md` only.
- Tests: `tests/test_header_m6.py` (3 tests).

## Checks run
- Syntax parse only. I still cannot run pytest/Streamlit in my sandbox (no network). The tests above are not executed.

## NOT verified / owner must check by hand
1. **Decide on the law expander**: stay removed, or come back as text built from `config/rules.yaml` (needs your sign-off on which rules/wording are public).
2. **Hotline 16131 — please verify by hand** with the Department of Environment. It is still shown in: sidebar (`DEPARTMENT_OF_ENVIRONMENT_HOTLINE_16131_`, Bangla digits), footer (`HOTLINE_LABEL: 16131`), and the community PDF (two English lines). I did not change or confirm it. The sidebar line and the PDF also say "file a complaint" style text; confirm that framing is OK under rule 8.
3. **"Data date" = file mtime.** On Streamlit Community Cloud the mtime is the checkout/deploy time, not when the data was produced. If you want the true date, add it to the parquet metadata or `config/dashboard.yaml` (I did not invent a schema).
4. **Native-speaker review** of the 4 changed labels.
5. Other places may still use "ঝুঁকি" (risk) wording in popups/reasons (`_priority_reason`, `RISK_INFO_FMT`); I only changed the labels the brief named. Say if you want a full wording audit.
6. Not touched: PDF English text (M7), nothing pushed to GitHub.

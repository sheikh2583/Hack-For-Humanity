# HANDOFF (Phase 2, pitch polish)

## Done: P0 baseline and design audit
- Unzipped `dhoa_claude_source_9da5d2.zip` (M0-M9 + bilingual toggle), restored `data/` and the PDF font from GitHub.
- Fixed the Inspector crash caused by `on_change` inside `st.form` (see `docs/P0_AUDIT.md`).
- `tests/test_inspector_m4.py` now uses `_wkey(...)` widget keys (the language-suffixed keys broke it).
- Screenshots + audit: `docs/screens/p0/`, `docs/P0_AUDIT.md`; `scripts/shoot_screens.py` re-creates them.
- Baseline benchmark recorded in the audit.

## Next step
P1 design system: one tokens file + generated CSS, colour-blind-safe priority palette with shapes,
self-hosted font, AA contrast, 44 px targets.

## Unverified
- Empty-state screenshot (my browser automation could not drive the selectboxes) and the PDFs: not captured.
- Community at 360 px: screenshot not captured in this pass.
- Real basemap tiles and a real phone: the sandbox blocks tiles, so the map is blank grey in screenshots.
- Page load time in a real browser: Chromium here is slow (list appears ~25 s after load); judge on your machine.
- Missing from the zip: `.github/workflows/keep_warm.yml`, `docs/DEMO_SCRIPT.md` (3 deploy tests fail because of it).

## Decisions
- Fixed the form crash first because P0 cannot be judged with a broken Inspector.
- English toggle left as is (you said you will fix it later).

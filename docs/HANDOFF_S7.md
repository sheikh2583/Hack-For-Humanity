# S7 handoff — Dhoa dashboard and demo polish

## Completed

- Changed Overview and About date labels to “Data as of” and the Bangla
  equivalent. The displayed date still comes from the processed dataset file;
  it is not the current date.
- Rewrote the public About summary to describe the app without public priority
  or siting-rule language. Added bilingual methods/limits and privacy sections.
- Replaced `demo_script.md` with timed English and Bangla public-to-staff
  walkthroughs. The report and staff note use `DEMO ONLY` labels.
- Added a dashboard-only quick start to README, separate from pipeline setup.
- Moved the two root Claude handoff notes into `docs/`. Kept `mobile/` source
  files in place; they are the Expo app, not duplicate handoff documents.

## Verification

- CPU-only checks: 58 targeted tests passed; two known S2 public-view tests
  were deselected because their existing assertions inspect priority strings
  inside the page CSS and generated dashboard text. Running them directly
  produced those two failures.
- `compileall` and `git diff --check` passed.
- In a real local browser with the current processed dataset, completed the
  place-search, labelled report submission, staff report badge/inbox, map,
  assignment, visited status, and labelled note flow in both Bangla and
  English. The test database was isolated at
  `X:\temp\dhoa_s7_browser\app.db`.
- Checked keyboard Tab and arrow navigation in the language controls.
- Existing design tests cover marker shapes/glyphs, contrast ratios, and
  accessible chart/list labels.
- Screenshots of the English and Bangla About pages and English place search
  were captured in the browser during verification.

## Not verified

- The browser run used the current local dataset and temporary SQLite file;
  a hosted deployment and its staff configuration were not checked.
- No mobile device/browser run or native-speaker review of the Bangla copy was
  performed.
- No model inference, training, pipeline run, or GPU task was performed.
- Demo records remain only in the temporary database outside the repository.

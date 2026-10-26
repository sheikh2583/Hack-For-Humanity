# Changelog

## 2026-10-26

- S3: Replaced the public Near me result table with responsive candidate cards for kiln type, nearest place, distance, and directions. Added Bangla and English labels, rendered the map before the cards on narrow screens, and styled public map clusters in one neutral colour.
- S4: Added the report storage interface, SQLite adapter, extent-based coordinate validation, public correction and missing-kiln forms, optional photo storage, privacy copy, and per-session abuse limit. Added a Streamlit import fallback and removed duplicate map-selectbox default seeding.
- S5: Added SQLite visit assignments/statuses and append-only notes, staff-only visit controls and My visit list, a status-managed report inbox with map navigation, and an open-report bell count. Added Bangla and English labels.
- S6: Added display-name-scoped saved Inspector filters, a staff activity log, optional visit-photo storage and display, and ordered Google Maps route links covering assigned stops. Kept CSV and kiln PDF exports in the Inspector Map path.
- S7: Added dataset-derived “Data as of” labels, neutral bilingual About methods/limits and privacy copy, a bilingual 60-second public-report-to-staff demo, and a dashboard-only quick start. Moved the root handoff notes into docs/.

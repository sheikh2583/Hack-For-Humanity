# Dhoa chatbot handoff

## Goal
Improve the floating Help chatbot orb so it feels modern, is larger and more eye-catching, has no button background, and floats visibly above the page. Keep the chatbot usable and accessible on desktop and mobile.

## Current state
- Chatbot UI and routing live in `app/streamlit_app.py` (`render_chatbot` and nearby helpers).
- Orb positioning and appearance live in `app/styles.py` under the local Help chatbot CSS.
- `app/chatbot.py` handles keyword-based replies; UI also supports matching districts, upazilas, and saved places.
- English and Bengali strings are in `app/strings_en.py` and `app/strings_bn.py`.
- The orb styling was just changed locally: 5.25rem desktop / 4.5rem mobile, transparent background and no border, drop shadow, subtle float animation, reduced-motion support.

## Constraints
- Follow `AGENTS.md` in this archive. Do not run GPU workloads.
- Do not show developer-facing advisory, verification, preprocessing, or legal-status text in the UI.
- Preserve the existing local/offline chatbot behavior and bilingual support unless intentionally changing it.
- Avoid broad unrelated edits. Do not start the Streamlit app unless explicitly requested.

## Included files
The archive contains the chatbot implementation and its direct UI, styling, translation, design-token, and test context. `app/streamlit_app.py` is included because its chatbot renderer and routing helpers are currently embedded in that module.

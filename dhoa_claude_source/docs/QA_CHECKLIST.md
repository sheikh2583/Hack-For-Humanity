# Manual QA checklist (M8)

Run `streamlit run app/streamlit_app.py` with the real data, then repeat at each width:
**360 px** (small phone), **412 px** (large phone), **768 px** (tablet), **1280 px** (desktop).
Use Chrome DevTools device mode, and one real phone over https for GPS.

## Every width
- [ ] Page loads with no error box; title and 4 header metrics readable; "data date" is not today's date.
- [ ] No horizontal page scroll. Font is Noto Sans Bengali (Network tab: `.woff2` 200, no Google Fonts request).
- [ ] Tap targets feel ≥ 44 px (buttons, select boxes, segmented control, expander headers).

## Inspector
- [ ] Sidebar filters: change several, press "ফিল্টার প্রয়োগ করুন" -> ONE rerun; reset works.
- [ ] Summary strip counts match the list; priority shown by shape (▲◆●) and colour.
- [ ] Select a kiln from the list and from the map -> detail card; 3 buttons side by side even at 360 px.
- [ ] Empty filter (e.g. Dhaka + Adabor) -> message + reset button.
- [ ] Pan and zoom the map: no spinner/"running" indicator, no snap-back (also: `DHOA_E2E=1 pytest tests/e2e`).
- [ ] CSV download opens with correct Bangla headers.

## Community
- [ ] Before choosing: prompt text. Picker is searchable (type "Savar").
- [ ] Choose an upazila -> all its kilns, no circle, map fits them, summary card correct.
- [ ] Choose a named place with radius 1 km -> either results or the empty-state with nearest distance and a one-click widen button; button works.
- [ ] Radius control disabled for district/upazila, with the note.
- [ ] "আমার অবস্থান ব্যবহার করুন": allow -> result, no page reload; deny -> Bangla message; on http (non-localhost) -> "insecure" message.
- [ ] Free-text fallback: a real name works; nonsense -> not-found message; offline -> unavailable message; a foreign city -> not found / outside message.
- [ ] A point outside the 5 districts -> message listing covered districts.
- [ ] PDF and CSV download; PDF opens (English text is expected, M7 flag).
- [ ] Pan and zoom the Community map: no rerun, no snap-back.

## Language toggle (বাংলা / English) - do on BOTH views at 1280 and 412 px
- [ ] Open DevTools console: no JavaScript errors at load, after each switch, and after clicking a marker.
- [ ] Switch Inspector bn -> en -> bn: header, filters, list, summary strip, detail card, CSV headers change language; the chosen district/area/type/priority filters and the selected kiln are unchanged.
- [ ] Map iframe stays 580 px high and is not blank after a switch (it rebuilds once because tooltip text is inside the map script; the view must re-fit to the same kilns). Pan/zoom afterwards still causes no rerun.
- [ ] Community: pick a place, switch language: the same place stays selected, results unchanged, labels/notice texts switch; with "use my location" the origin label switches too; an empty-state message switches.
- [ ] `?lang=en` in the URL opens English; switching updates the URL.
- [ ] PDF/CSV downloaded in each language open correctly (the per-kiln PDF is not translated yet).

## Wording
- [ ] No "violation/hazardous/illegal" wording in either language; no legal distances shown.
- [ ] Native speakers read the Bangla copy and the English copy (`strings_bn.py`, `strings_en.py`).

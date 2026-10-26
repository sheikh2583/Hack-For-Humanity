# Map-first layout: handoff

## Why
The map is the main thing, but you had to scroll the sidebar to reach all filters and scroll the page to find the map. Now: map first, everything needed above it is one slim band.

## What changed (Map tab / Inspector)
- **Header = one row**: title | tabs | "How to use" | language. The subtitle, the separate full-width help bar, the extra caption and the divider are gone on Map and Near me (Overview/About keep their subtitle). On phones the row wraps: title + language, then tabs.
- **Summary strip = one slim line** (value and label side by side) instead of five tall tiles; the "relative shares" note stays under it.
- **Map left and wider (3:2), list right**. On phones the map is first, then the list.
- **Map toolbar** directly above the map: legend, density toggle, map type (street/satellite). The map type moved out of the sidebar.
- **Map height follows the window**: `clamp(420px, 100dvh - 300px, 860px)` on desktop (phone rule unchanged). The priority list's frame uses the same idea (`window height - 250`).
- Report PDF button / "select a kiln" hint moved **below** the map. The selected-kiln card is still under the map.
- **Sidebar fits without scrolling**: removed the "Search" title and hint and the "Filters" heading; priority is now three pills (▲ High ◆ Medium ● Low) instead of the tall tag box; the CSV download moved to the list header; tighter spacing. Order: District, Area, Priority, Kiln type, Apply, Reset, hotline line.
- Tests: `tests/test_layout_m11.py` (6 source/CSS checks); `test_views_m8` language test adjusted for pills.

## Verified / not
- Python and CSS parse; the static layout checks in `test_layout_m11.py` were evaluated by a script here. **Not run**: pytest, Streamlit, a browser. I have not seen the result on screen.

## Please check in the browser (1366x768 laptop first)
1. Map fully visible without scrolling; sidebar needs no scroll. If the map is cut off or leaves a gap, change the `300px` in `styles.py` (`.st-key-dhoa_map_frame iframe`) and `250` in `priority_candidate_list/index.html`.
2. Pills: click two, press Apply; switch language; selection stays and filters give the same rows. (`st.pills` is not exposed by Streamlit's AppTest, so this is browser-only.)
3. Changing map type now reruns only the map block (it lives in the map fragment).
4. Phone width (412): header wraps to two rows, toolbar wraps, map then list.
5. Selected-kiln details are below the map: after clicking a kiln you still scroll to see the card (the marker popup shows the key facts and links on the map). Say if you want the card beside/over the map instead.
6. The Community tab layout is unchanged (list left, map right). Say if you want the same map-first treatment there.

# M5 — Community redesign: handoff

## CHANGELOG (M5)
- **Three steps on one screen**: 1 Where, 2 How far, 3 Results (`render_community_view`).
- **Step 1 – one searchable picker** built from the data (`community.build_places`): 5 districts, only upazilas that have kilns, and known `nearest_place` names (grouped per district), each label with its kiln count. Places with no data are no longer offered, so no valid choice is empty for lack of data.
- **"Use my location"** is now a bidirectional Streamlit component (`app/components/geolocate/`). No page reload, no query params, no `alert()`. Errors (denied / unsupported / insecure context / timeout / unavailable) become Bangla messages under the picker. The old `components.html` button and the `_geo_lat` / `gps_lat` handlers are gone.
- **Geocoding fallback kept** (your brief's assumption), tucked in an expander: Nominatim (country=BD) then Photon, 8 s timeout, process-wide 1.1 s rate limit, results outside a coarse Bangladesh box discarded, cached 24 h (`st.cache_data(ttl)`); "not found" is cached, outages are not.
- **Outside coverage**: a geocoded or GPS point not near any of the 5 districts shows a Bangla message listing the covered districts (`community.covered_district`).
- **Step 2 – radius** 1 / 2 / 5 / 10 km, default 5 km. For a district or upazila the control is disabled with a note and **all kilns of the area** are shown (no radius, view fitted to the kilns, no circle).
- **Step 3 – results**: summary card ("N kilns within X km, K high priority" plus ▲◆● counts), list, map, PDF and CSV. Map keeps the M3 behaviour (`returned_objects=["last_object_clicked"]`, circle/highlight via `feature_group_to_add`).
- **Empty state**: "No kilns within 1 km. Nearest is 2.3 km away (area)" and a one-click button for the smallest radius that reaches it (`radius_to_reach`); if even 10 km is not enough, the message says so.
- **Dead path removed**: `get_filtered_gdf` (community) now reads `community_origin` / `community_place_key` / `community_radius_m`. `_community_area_centroid`, `_reset_community_*`, `community_centroid`, `community_filter_*`, `community_search_*` removed. District/upazila alone now always gives a result.
- PDF/CSV: whole-area results print "-" instead of a distance and say "in <area>" (radius 0 means whole area).
- Copy: new `strings.C_*` block; `HELP_COMMUNITY` and the community caption rewritten for the three steps.
- Tests: new `tests/test_community_m5.py` (11 pure tests + 3 AppTests that skip without the parquet); `test_dashboard_m2.py` community-filter test updated to the new session contract.

## Checks run
- The 11 pure tests pass here **with `kd.distances_from_point_m` replaced by a haversine stub**, because this sandbox has no network, so no `pyproj`, `pytest` or `streamlit`. Syntax of all changed Python files was parsed OK.
- NOT run here: the real test suite, the AppTests, the app itself, anything in a browser.

## NOT verified / owner must check by hand
1. **Run `pytest tests/test_community_m5.py tests/test_dashboard_m2.py tests/test_map_stability.py`** on your machine first. I could not execute any Streamlit code; expect possible small fixes (a name I mistyped, an AppTest selector).
2. **GPS in a browser**: needs https or localhost. Check Streamlit's component iframe allows geolocation on your deployment (Community Cloud), that granting works without a reload, and that denying shows the Bangla message. `window.isSecureContext` false gives the "insecure" message.
3. **Upazila names are English** in the data, so the picker is searched by English spelling (placeholder says "যেমন: Savar"). Your brief's example "সাভার" will not match anything. To type Bangla you need a Bangla-name mapping for 58 upazilas (I did not invent one). Please decide.
4. **Named places** (`nearest_place`): their centre is the mean position of the kilns that reference that name, not the place's true coordinate (the data has none). Fine for "kilns around here", but confirm you are happy with it.
5. **District and upazila choices list all their kilns** (e.g. all Dhaka kilns) instead of a radius. The brief only specified this for upazilas; I applied it to districts too since a radius around a district centre is meaningless. Say if you want a radius for districts.
6. **Coverage rule is a heuristic**: a point is "covered" if it lies in a district's kiln bounding box widened by 10 km (data has no district polygons). A Bangladesh bounding box (20.5–26.7 N, 88.0–92.8 E) filters geocoder hits. Both are display/UX heuristics, not legal thresholds; please sanity-check on the edge of Dhaka/Gazipur.
7. **Native-speaker review of all `C_*` copy** (placeholder, helper text, errors, summary/empty-state sentences).
8. **Geocoder terms**: Nominatim's public server has a usage policy (1 req/s, identifying user agent; not for heavy use). Fine for a demo; use a paid/self-hosted geocoder for production.
9. Still open from other modules: header metric labels, law expander, "last updated" date, hotline 16131 (M6); the PDF still has English text and the hotline (M6/M7); old unused strings (`SEARCH_BY_NAME`, `E_G_ASHULIA`, …) remain in `strings.py`; the `Transformer` import in `streamlit_app.py` is now unused.
10. GitHub not touched; nothing pushed.

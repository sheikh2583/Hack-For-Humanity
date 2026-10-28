"""English catalogue for the Dhoa dashboard (read through ``strings``).

Input schema: none (constants only). Output schema: module-level ``str`` constants
with exactly the same names and the same ``str.format`` fields as ``strings_bn``;
``tests/test_strings_i18n.py`` enforces this. The English copy needs a native-speaker
review before release.
"""

from __future__ import annotations

APP_TITLE = 'ধোঁয়া'  # brand name, shown in Bangla in both languages
CHANDRABINDU = 'ঁ'

ALL_TYPES = 'All types'
ZIGZAG_KILN = 'Zigzag kiln'
FIXED_CHIMNEY_KILN = 'Fixed chimney kiln'
COL_KILN_ID = 'Kiln ID'
COL_LATITUDE = 'Latitude'
COL_LONGITUDE = 'Longitude'

DISTRICT = 'District'
COL_UPAZILA = 'Upazila'
COL_NEAREST_PLACE = 'Nearest place'
COL_DISTANCE_M = 'Distance (m)'

PRIORITY = 'Priority'
COL_BREACH_COUNT = 'Number of rule signals'
METRIC_TOTAL_KILNS = 'Total kilns'
METRIC_HIGH_PRIORITY_KILNS = 'High-priority candidates'
METRIC_RULE_VIOLATIONS = 'Rule signals'
METRIC_LAST_UPDATED = 'Data as of'
METRIC_TOTAL_CANDIDATES = 'Total candidates'
METRIC_ESTIMATED_AREA = 'Approx. area (sq km)'
METRIC_PRIMARY_SIGNAL = 'Main rule signal'
METRIC_NEW_CANDIDATES = 'New candidates'
METRIC_RULE_SIGNALS = 'Rule signals'

HIGH = 'High'
MEDIUM = 'Medium'
LOW = 'Low'
UNCLASSIFIED = 'Unclassified'

ALL_DISTRICTS = 'All districts'
DISTRICT_CHAPAINAWABGANJ = 'Chapainawabganj'
DISTRICT_GAZIPUR = 'Gazipur'
DISTRICT_RAJSHAHI = 'Rajshahi'
DISTRICT_DHAKA = 'Dhaka'
DISTRICT_CHITTAGONG = 'Chittagong'
UNKNOWN_AREA = 'Unknown area'

NEAR_SCHOOL = 'Near school'
NEAR_HOSPITAL = 'Near hospital'
NEAR_SETTLEMENT = 'Near settlement'
NEAR_RAILWAY = 'Near railway'
NEAR_WETLAND = 'Near wetland'
NEAR_GOVERNMENT_FOREST = 'Near government forest'
FIXED_CHIMNEY_TECHNOLOGY = 'Fixed chimney technology'
SCHOOL = 'school'
HOSPITAL = 'hospital'
SETTLEMENT = 'settlement'
RAILWAY = 'railway'
WETLAND = 'wetland'
GOVERNMENT_FOREST = 'government forest'
NO_RULE_SIGNALS_RECORDED = 'No rule signals recorded'

STREET_MAP = 'Street map'
SATELLITE_IMAGERY = 'Satellite imagery'
MAP_TYPE = 'Map type'
REPORT_COMMUNITY_NOTE = 'This report is for community awareness only and is provided for information purposes.'
MY_LOCATION = 'My location'
FIND_KILNS_NEAR_YOU = 'Find kilns near you'
LISTEN_TO_THE_GUIDE = '🔊 Listen to the guide'
AUDIO_GUIDE_COMING_SOON = '🔊 Audio guide coming soon'
AREA_THANA = 'Area (upazila)'
SEARCH_RADIUS_METRES = 'Search radius (metres)'
SEARCH_BY_NAME = 'Search by name'
E_G_ASHULIA = 'e.g. Ashulia'
SEARCH = '🔍 Search'
OR_USE_YOUR_CURRENT_LOCATION = '**Or use your current location:**'
USE_MY_LOCATION = 'Use my location'
YOUR_LOCATION = 'Your location'
PLEASE_ENTER_A_LOCATION_NAME = '⚠️ Please enter a place name to search.'
SEARCHING = 'Searching…'
LOCATION_NOT_FOUND_TRY_A_DIFFERENT_SPELL = "⚠️ Place not found. Try another spelling or write it like 'Ashulia, Savar'."
SELECT_A_DISTRICT_AND_SEARCH_FOR_A_PLACE = 'Select a district to see kilns.'
NEARBY_KILN_CANDIDATES = 'Nearby kiln candidates'
DOWNLOAD_REPORT = 'Download report'
REPORT_GENERATION_FAILED_PLEASE_TRY_AGAI = 'Could not create the report. Please try again.'
DISTANCE_M = 'Distance (metres)'
AREA = 'Area'
KILN_TYPE = 'Kiln type'
DIRECTIONS = 'Directions'
NO_DATA = 'No data'
GET_DIRECTIONS = 'Get directions'
DOWNLOAD_COMMUNITY_CSV = 'Download community list'
AREA_MAP = 'Area map'
SEARCH_POINT_LABEL = 'Search point'
AREA_CENTROID_LABEL = 'Centre of the selected area'
HIGH_PRIORITY = 'High priority'
FOREST = 'forest'
FOREST_DATA_UNAVAILABLE = '🌲 No forest data on the map'
OUTSIDE_THRESHOLD = 'Outside threshold'
NEW_CANDIDATE_2025_26 = 'New (2025–26)'
PREVIOUSLY_DETECTED_2023_24 = 'Previously detected (2023–24)'
NEW_SUFFIX = ' [new]'
RULE_SIGNALS_HEADING = 'Rule signals:'
POPUP_LINKS = '[🗺️ Directions] [📍 Map] [🌍 Earth]'
KILN_CANDIDATE = 'Kiln candidate'
RULE_SIGNALS = 'Rule signals'
MAP = 'Map'
REPORT_ID = 'Report ID'
VIEW_KILN = 'View kiln'

BANGLADESH_BRICK_KILN_MONITORING_DASHBOA = 'Bangladesh Brick Kiln Monitoring Dashboard'
CHOOSE_VIEW = 'Choose view'
VIEW_INSPECTOR = '🔒 Inspector Portal'
VIEW_COMMUNITY = 'Kilns near me'
HOW_TO_USE = 'How to use'
HELP_COMMUNITY = """
**Using Kilns near me**

1. Type a district, upazila, or nearby place in the search box.

2. Select the correct location from the **Matching areas** list.

3. Alternatively, select **Use my location** and allow browser location access.

4. When a named area is selected, all kiln candidates in that area are shown, so the distance selector is not required.

5. When using the current location, choose **1 km**, **2 km**, **5 km**, or **10 km**.

6. Review kiln candidates on the map and select a marker to see available information.

7. To report a missing kiln, open **Report a kiln missing from the map**.

8. Enter latitude and longitude, add a short note, and optionally add contact information and a photo.

9. These are satellite-based kiln candidates for monitoring and field verification, not final legal or enforcement decisions.

[▶ Play voice guide — audio coming soon]
"""
HELP_INSPECTOR = """
**Using the Inspector Portal**

1. **Dashboard:** View total candidates, high-priority candidates, district summaries, and upazilas with the most candidates.

2. **Map:** Filter by district, area/upazila, priority, and kiln type. Select **Apply filters** to use the filters, or **Reset filters** to clear them. Use the **Street map** and density heatmap to understand locations, and download the filtered list with **Download filtered list (CSV)**.

3. **View kiln:** Open an individual candidate and review its details. Available actions include **Download PDF**, **Open location on map**, **Directions**, **Street View**, **Google Earth**, **Update visit status**, **Assign to me** or assign the visit, **Add a note**, and **Attach a visit photo**. Select **Save updates** when finished.

4. **Work:** Manage assigned visits, saved filters, visit status, priority, distance, routes, map routes, and directions.

5. **Reports:** Review community reports and rule signals, open the location, select **Mark reviewed** or **Mark resolved**, and download reports.

6. Sign out when finished, especially on shared computers.

7. Map detections, distance indicators, and priority levels support field verification and are not final enforcement decisions.

[▶ Play voice guide — audio coming soon]
"""
CHOOSE_A_DISTRICT_AND_UPAZILA_YOU_MAY_EN = 'Find kiln candidates near your area in three steps.'
BROWSE_THE_KILN_LIST_AND_MAP_USE_FILTERS = 'Browse the ranked kiln list and map, and use the filters to find candidates.'
NONE = 'None'
RISK_SCOPE_SCHOOLS_HOSPITALS = 'near schools and hospitals'
RISK_SCOPE_SIGNALS = 'with rule signals'
SEARCH_2 = 'Search'
ALL_AREAS = 'All areas'
SEARCH_RADIUS = 'Search radius'
SELECT_AN_UPAZILA_TO_ENABLE_THE_RADIUS = 'Select an upazila to enable the radius'
FILTERS = 'Filters'
FILTER_DISTRICT_HINT = 'Choose a district to narrow the available area list.'
DOWNLOAD_FILTERED_CSV = '⬇ Download filtered list (CSV)'
DEPARTMENT_OF_ENVIRONMENT_HOTLINE_16131_ = 'Department of Environment hotline: 16131 | [doe.gov.bd](https://doe.gov.bd)'
RESET_FILTERS = '🔄 Reset filters'
APPLY_FILTERS = 'Apply filters'
DISTANCE_FROM_GOVERNMENT_FOREST = 'Distance from government forest'
KILN_TYPE_2 = 'Type'
STATUS_NEW = 'New candidate (2025–26)'
STATUS_KNOWN = 'Previously detected (2023–24 survey)'
DETECTION_STATUS = 'Detection status'
COORDINATES = 'Coordinates'
DIRECTIONS_2 = '🗺️ Directions'
STREET_VIEW = '📍 Street view'
GOOGLE_EARTH = '🌍 Google Earth'
COULD_NOT_GENERATE_THE_REPORT_PLEASE_TRY = '❌ Could not create the report. Please try again.'
DOWNLOAD_SELECTED_KILN_PDF = '📄 Download PDF of the selected candidate'
COULD_NOT_GENERATE_THE_REPORT = 'Could not create the report.'
SELECTED = '✓ Selected'
PRIORITY_LIST = '🔥 Priority list'
NO_CANDIDATES_MATCH_THESE_FILTERS = 'No candidates match these filters.'
MARKER_COLOUR_SHOWS_PRIORITY_BOLD_BORDER = 'Marker shape and colour show priority (▲ high, ◆ medium, ● low); the bold ring marks the selected candidate.'
SELECT_A_CANDIDATE_FROM_THE_LIST_OR_MAP_ = 'Select a candidate from the list or map to get a PDF.'
COULD_NOT_RENDER_THE_MAP = 'Could not show the map.'
TAP_ANY_KILN_MARKER_ON_THE_MAP_TO_VIEW_D = 'Tap any kiln marker on the map to see details and a report.'
CLEAR_KILN_SELECTION_SHOW_ALL_KILNS = 'Clear selection · Show all kilns'
HOTLINE_LABEL = 'ধোঁয়া · DoE hotline'
LOADING_KILN_DATA_THIS_MAY_TAKE_A_FEW_SE = 'Loading data. This may take a few seconds…'
COULD_NOT_LOAD_DASHBOARD_DATA_PLEASE_TRY = '❌ Could not load the data or dashboard. Please try again later.'
RETRY_LOADING_DATA = 'Try again'
DASHBOARD_DATA_IS_UNAVAILABLE = '❌ The dashboard data is not available. Process the data first.'
COULD_NOT_RENDER_THE_DASHBOARD = '❌ Could not show the dashboard.'

RISK_INFO_FMT = '{2} high-priority candidates {1} found in {0}.'
SELECTED_KILN_TITLE_FMT = '✅ Selected candidate · Kiln #{0}'
CENTROID_OF_AREA_FMT = 'centre of the selected area {0}'
POPUP_TITLE_FMT = 'Kiln candidate · {0}'
POPUP_PRIORITY_FMT = 'Priority: {0}'
POPUP_AREA_FMT = '📍 Area: {0}'
POPUP_REPORT_ID_FMT = '[📄 Report ID: {0}]'
DISTANCE_FROM_FMT = 'Distance from {0}'
NO_KILNS_IN_AREA_FMT = "No kiln data found for '{0}'."
COORDS_FMT = '{0:.5f}° N, {1:.5f}° E'
KM_FMT = '{0:.1f} km'
M_FMT = '{0:,.0f} m'
METRES_FMT = '{0:,.0f} metres'
COMMUNITY_MAP_CAPTION_FMT = 'The blue circle shows {1:g} km from {0}. Red, orange and green dots show kiln priority; tap a dot for details.'
M_DOT_FMT = '{0:,.0f} m'
CANDIDATES_MATCH_FMT = '{0:,} candidates match the filters'
REASON_FROM_FMT = '{1:,.0f} metres from {0}'
NO_KILNS_IN_RADIUS_FMT = '✅ No kilns found within {0:g} km.'
KILNS_WITHIN_RADIUS_FMT = 'Kilns within {0:g} km'
PAGE_LOADING = 'Loading the page, please wait…'

RAIL_HINT = 'Choose your filters, then press “Apply filters”.'
SUMMARY_MATCHING = 'Matching candidates'
SUMMARY_HIGH = 'High priority'
SUMMARY_MEDIUM = 'Medium priority'
SUMMARY_LOW = 'Low priority'
SUMMARY_NEW = 'New candidates'
PRIORITY_NOTE = 'High, medium and low priority are relative shares of the ranking of all candidates (top 20%, next 40%, remaining 40%). They are not an absolute measure of risk.'
PRIORITY_LEGEND = 'Symbols'
EMPTY_FILTER_HINT = 'Change the filters and try again, or clear all filters.'
LOADING_MAP = 'Preparing the map…'
RETRY = '🔄 Try again'
DETAIL_HINT = 'Select a candidate from the list, or click a marker on the map.'

C_STEP1 = '1. Where to look?'
C_PLACE_LABEL = 'Search your area'
C_PLACE_PLACEHOLDER = 'Type an area name (e.g. Savar)'
C_PLACE_HELP = 'Type a few letters to find an area, or enter a place name and press Enter.'
C_PLACE_SUGGESTIONS = 'Matching areas'
C_PLACE_SUGGESTION_PLACEHOLDER = 'Choose a matching area'
C_GEO_SUGGESTION_FMT = 'Search Bangladesh for “{0}”'
C_PLACE_LABEL_FMT = '{name} · {count} kilns'
C_GPS_LABEL = '📍 Use my location'
C_GPS_BUSY = 'Finding your location…'
C_GPS_OK = 'Your location was found.'
C_GPS_DENIED = 'Location permission was not given. Allow it in your browser settings, or search for your area above.'
C_GPS_UNSUPPORTED = 'This browser cannot find your location. Search for your area above.'
C_GPS_INSECURE = 'Location needs a secure (https) connection. Search for your area above.'
C_GPS_UNAVAILABLE = 'Your location could not be found. Search for your area above.'
C_GPS_TIMEOUT = 'Finding your location is taking too long. Try again, or search for your area.'
C_GPS_HINT = 'Your browser will ask for location permission. If blocked, use the search box above.'
C_GEO_EMPTY = 'Type a name to search.'
C_GEO_SEARCHING = 'Searching for the place…'
C_GEO_NOT_FOUND = 'No place with this name was found in Bangladesh. Try another spelling, or search for a covered area above.'
C_GEO_UNAVAILABLE = 'Searching by name is not available right now. Search for a covered area above, or try again in a little while.'
C_OUTSIDE_FMT = '“{0}” is outside the districts our data covers. Covered districts: {1}. Pick a place in one of them.'
C_STEP2 = '2. How far?'
C_RADIUS_LABEL = 'Distance'
C_RADIUS_OPTION_FMT = '{0:g} km'
C_RADIUS_HELP = 'Kilns within this distance of the chosen place will be shown.'
C_RADIUS_AREA_NOTE = 'All kilns in the whole area are shown, so you do not need to choose a distance.'
C_STEP3 = '3. Results'
C_PICK_PROMPT = 'To start, search for your area above, or press “Use my location”.'
C_SUMMARY_RADIUS_FMT = '{2:,} kilns within {0:g} km of {1}'
C_SUMMARY_AREA_FMT = '{1:,} kilns in {0}'
C_SUMMARY_HIGH_FMT = '{0:,} of them high priority'
C_EMPTY_NEAREST_FMT = 'No kilns within {0:g} km. The nearest kiln is {1:.1f} km away ({2}).'
C_EMPTY_FAR_FMT = 'No kilns within {0:g} km. The nearest kiln is {1:.1f} km away ({2}), beyond the largest distance you can choose.'
C_EMPTY_NONE = 'No kiln data was found here. Pick another place.'
C_SHOW_WITHIN_FMT = 'Show within {0:g} km'
C_LIST_TITLE = 'Nearby kilns'
C_CARD_DISTANCE_FMT = 'Distance: {0}'
C_CARD_PLACE_FMT = 'Nearest place: {0}'
C_REPORT_EXISTING_TITLE = 'Report this kiln'
C_REPORT_CARD_ACTION = 'Report this kiln'
C_REPORT_EXISTING_REASON = 'What is the issue?'
C_REPORT_REASON_LOCATION = 'Wrong location'
C_REPORT_REASON_NOT_KILN = 'This is not a brick kiln'
C_REPORT_REASON_CONCERN = 'Possible environmental or siting concern'
C_REPORT_REASON_OTHER = 'Another issue'
C_REPORT_NEW_TITLE = 'Report a kiln missing from the map'
C_REPORT_LAT = 'Latitude'
C_REPORT_LON = 'Longitude'
C_REPORT_NOTE = 'Short note'
C_REPORT_CONTACT = 'Contact information (optional)'
C_REPORT_PHOTO = 'Photo (optional)'
C_REPORT_SUBMIT = 'Submit report'
C_REPORT_SENT = 'Your report was submitted. Thank you.'
C_REPORT_SUCCESS_BUTTON = 'Successfully reported'
C_REPORT_INVALID_COORDS = 'That location is outside the area covered by our data. Enter coordinates for a place on the map.'
C_REPORT_COORDS_HELP = 'Coordinates must fall within the area shown on the map.'
C_REPORT_NO_EXTENT = 'Area data for reports is not available right now.'
C_REPORT_RATE_LIMIT = 'Several reports were sent recently. Please try again later.'
C_REPORT_FAILED = 'Could not submit your report. Please try again.'
C_REPORT_PRIVACY = 'We store the location, reason, note, submission time, and any optional contact information or photo you submit with this report. We do not collect other information about you.'
C_REPORT_HONEYPOT = 'Website'
C_MAP_CAPTION_RADIUS_FMT = 'The blue circle shows {1:g} km from {0}. Each marker is one kiln; tap a marker for details.'
C_MAP_CAPTION_AREA_FMT = 'The map shows all kilns in {0}. Each marker is one kiln; tap a marker for details.'

# P2: landing hero and top navigation (flag for native-speaker review)
NAV_OVERVIEW = 'Overview'
NAV_MAP = 'Map'
NAV_NEAR_ME = 'Kilns near me'
NAV_ABOUT = 'About'
HERO_MISSION = 'Brick kilns found in satellite images, mapped and ranked by priority.'
HERO_SUB = 'Explore every candidate on the map, or find the ones near your home.'
HERO_CTA_MAP = 'Explore the map'
HERO_CTA_NEAR_ME = 'Find kilns near me'
HERO_METRIC_DISTRICTS = 'Districts covered'
ABOUT_TITLE = 'About Dhoa'
ABOUT_BODY = (
    'Dhoa helps people explore kiln candidates detected in Sentinel-2 imagery. '
    'The map also shows nearby features from mapped data.'
)

# P3: overview charts and district comparison
OV_DISTRICTS_TITLE = 'Kiln candidates by district'
OV_DISTRICTS_HINT = 'Select a district name to open it on the map.'
OV_OPEN_DISTRICT_FMT = 'Open {0} on the map'
OV_SERIES_TOTAL = 'All candidates'
OV_SERIES_HIGH = 'High priority'
OV_UPAZILAS_TITLE = 'Upazilas with the most candidates'
OV_COL_CANDIDATES = 'Candidates'
OV_COL_HIGH = 'High priority'
OV_TYPES_TITLE = 'Kiln types'
OV_TYPE_OTHER = 'Other or unknown'
OV_SHARE_FMT = '{0:.0f}%'
OV_NO_DATA = 'No data to show.'

# --- P4: inspector ---
LEGEND_TITLE = 'Marker key'
HEAT_TOGGLE = 'Show density heatmap'
HEAT_HELP = 'Shades areas where many kilns sit close together. It does not show risk.'
DETAIL_DISTANCES_TITLE = 'Distance to nearby places'
DETAIL_WITHIN_FMT = 'Within {0}'
DETAIL_BEYOND_FMT = 'Beyond {0}'
DETAIL_STATE_UNKNOWN = 'Not available'

# --- P7: trust, states, About ---
HOTLINE_LINE_FMT = 'Department of Environment hotline: {0}'
DOE_WEB_LINE = 'Department of Environment: [doe.gov.bd](https://doe.gov.bd)'
FOOTER_WEB_LABEL = 'Department of Environment: doe.gov.bd'
CONTACT_CALL = 'Call'
CONTACT_SMS = 'SMS'
HOW_TITLE = 'How it works'
HOW_1_HEAD = 'Satellite images'
HOW_1_BODY = 'Sentinel-2 images of five districts are collected for one dry season.'
HOW_2_HEAD = 'Detection'
HOW_2_BODY = 'A model finds brick kiln candidates in the images and records their position and type.'
HOW_3_HEAD = 'Rule check'
HOW_3_BODY = 'Each candidate is compared with mapped schools, hospitals, settlements, railways, forests and wetlands.'
HOW_4_HEAD = 'Ranking'
HOW_4_BODY = 'Candidates are placed in High, Medium and Low priority, relative to each other and not as absolute risk.'
ABOUT_DATA_TITLE = 'Data'
ABOUT_DATA_DATE = 'Data as of'
ABOUT_SOURCES = 'Sources'
ABOUT_SOURCES_VALUE = 'Sentinel-2 satellite imagery; OpenStreetMap map features'
ABOUT_COVERAGE = 'Coverage'
ABOUT_COVERAGE_FMT = '{0} districts, {1} kiln candidates'
ABOUT_TEAM = 'Team'
ABOUT_METHODOLOGY = 'Read the methodology and limitations'
ABOUT_METHODS_TITLE = 'Methods and limits'
ABOUT_METHODS_BODY = (
    'Kiln candidates shown here come from Sentinel-2 imagery. Nearby-place details use '
    'OpenStreetMap features available to Dhoa; a place missing from map data may not appear. '
    'Coverage depends on the available imagery and map data. Submitted reports go to the staff inbox.'
)
ABOUT_PRIVACY_TITLE = 'Privacy'
ABOUT_PRIVACY_BODY = (
    'Public use does not save a user profile or search history. If you submit a report, '
    'its location, reason, note, submission time, and any optional contact information or photo '
    'are stored for staff to review.'
)
STATE_RETRY = 'Try again'
STATE_ERROR_TITLE = 'Something went wrong'
STATE_ERROR_BODY = 'This part of the page could not be shown. Your filters are kept. Please try again.'
STATE_DATA_TITLE = 'The data could not be loaded'
STATE_DATA_BODY = 'Please check your connection and try again in a moment.'
STATE_LOADING = 'Loading kiln data…'
LIST_ARIA_LABEL = 'Kiln candidates'
LIST_ARIA_SELECT_FMT = '{0}: {1}'

# --- P10: voice guide ---
VOICE_READ_ALOUD = '🔊 Read aloud'
VOICE_STOP = '⏹ Stop'
VOICE_NO_VOICE = 'This browser has no voice for this language. Please read the guide instead.'
VOICE_TRANSCRIPT = 'Read the text'
VOICE_INSPECTOR_SCRIPT = 'Welcome to the Inspector view. Here you can explore every kiln candidate on the map. First, open the filters on the left. Choose a district, area, kiln type, priority or rule signal, then press Apply filters. Next, pick a kiln from the priority list, or tap a marker on the map. Its details appear below, including distances to nearby schools, hospitals and other places. You can switch between the street map and satellite imagery, and turn on the density heatmap, which shows where many kilns sit close together. It does not show risk. To keep a record, download the filtered list as a CSV file, or a PDF report for the selected kiln. High, medium and low priority are relative groups across all candidates. They are not an absolute measure of risk.'
VOICE_COMMUNITY_SCRIPT = 'Welcome to Dhoa. This page helps you find brick kiln candidates near you. Step one: type a few letters to search for your district, upazila or nearby place, then choose a suggestion. Or press Use my location. Step two: choose how far. Pick a distance in kilometres. If you choose a whole upazila or district, every kiln in that area is shown. Step three: see the results. You get a short summary, a list and a map. Tap a marker on the map to see details for that kiln. You can download a report or the list to share. Priority colours are relative to each other. They are not an absolute measure of risk.'

# --- S1: four sections, Inspector Portal sign-in
NAV_INSPECTOR = '🔒 Inspector Portal'
PORTAL_SIGNIN_TITLE = 'Inspector Portal'
PORTAL_SIGNIN_HINT = 'This area is for staff. Enter your name and password to continue.'
PORTAL_PASSCODE = 'Password'
PORTAL_NAME = 'Your name'
PORTAL_SIGN_IN = 'Sign in'
PORTAL_WRONG_PASSCODE = 'That password is not correct. Please try again.'
PORTAL_SIGNIN_UNAVAILABLE = 'Staff sign-in is not available right now.'
PORTAL_DEMO_CREDENTIALS_HINT = 'DoE Inspector'
PORTAL_FILL_DEMO_CREDENTIALS = 'Continue as DoE Inspector'
PORTAL_PASSWORD_REQUIREMENTS = 'At least 12 characters, with uppercase and lowercase letters, a number, and a symbol.'
PORTAL_FORGOT_PASSWORD = 'Forgot password?'
PORTAL_REGISTER = 'Register'
PORTAL_ACCOUNT_ACTION_UNAVAILABLE = 'Password recovery and account registration are not configured yet.'
PORTAL_DEMO_INSPECTOR = 'DoE Inspector'
PORTAL_DEMO_CREDENTIALS_FMT = 'Demo credentials — Name: {0} · Password: {1}'
PORTAL_SIGNED_IN_FMT = 'Signed in: {0}'
PORTAL_SIGN_OUT = 'Sign out'
PORTAL_TAB_DASHBOARD = 'Dashboard'
PORTAL_TAB_MAP = 'Map'
PORTAL_TAB_WORK = 'Work'
PORTAL_TAB_REPORTS = 'Reports'
PORTAL_TAB_REPORTS_FMT = 'Reports ({0})'
PORTAL_TABS_LABEL = 'Inspector Portal sections'
PORTAL_SOON_TITLE = 'Coming soon'
PORTAL_SOON_BODY = 'This section will be available in the next update.'
WORK_STATUS = 'Visit status'
WORK_NOT_VISITED = 'Not visited'
WORK_ASSIGNED = 'Assigned'
WORK_VISITED = 'Visited'
WORK_CONFIRMED_ACTIVE = 'Confirmed active'
WORK_NOT_A_KILN = 'Not a kiln'
WORK_ASSIGN_TO_ME = 'Assign to me'
WORK_SAVE_STATUS = 'Save status'
WORK_ADD_NOTE = 'Add note'
WORK_NOTE_HINT = 'Write a note'
WORK_HISTORY = 'Visit history'
WORK_CURRENT_ASSIGNEE = 'Assigned to: {0}'
WORK_MY_LIST = 'My visit list'
WORK_STATUS_FILTER = 'Filter by status'
WORK_SORT = 'Sort by'
WORK_SORT_PRIORITY = 'Priority'
WORK_SORT_DISTANCE = 'Distance'
WORK_DISTANCE_ORIGIN = 'Distance from'
WORK_EMPTY = 'No visits match these filters.'
WORK_EMPTY_MAP_HINT = 'Choose a kiln on the Inspector Map and assign it to yourself to add it to your visit list.'
WORK_OPEN_INSPECTOR_MAP = 'Open Inspector Map'
WORK_ALL = 'All visits'
WORK_OPEN_MAP = 'Open on map'
WORK_DIRECTIONS = 'Directions'
WORK_ROUTES = 'Routes for my visits'
WORK_ROUTE_FMT = 'Open route {0} ({1}–{2})'
WORK_ROUTE_NOTE = 'The route starts at the first listed kiln and follows the list order. Google Maps calculates the roads.'
WORK_VISIT_PHOTO = 'Visit photo'
WORK_ATTACH_PHOTO = 'Attach photo'
WORK_PHOTO_SAVED = 'Visit photo saved.'
WORK_PHOTO_INVALID = 'Choose a JPEG, PNG, or WebP image.'
WORK_ACTIVITY = 'Recent activity'
WORK_ACTIVITY_VISIT = 'Visit status or assignment changed'
WORK_ACTIVITY_NOTE = 'Visit note added'
WORK_ACTIVITY_PHOTO = 'Visit photo added'
WORK_ACTIVITY_FILTER_SAVED = 'Saved filter created or updated'
WORK_ACTIVITY_FILTER_DELETED = 'Saved filter deleted'
WORK_ACTIVITY_REPORT = 'Report status changed'
WORK_ACTIVITY_STATUS_FMT = 'Status: {0}; assigned to: {1}'
SAVED_FILTERS = 'Saved filters'
SAVED_FILTER_NAME = 'Filter name'
SAVED_FILTER_SAVE = 'Save current filters'
SAVED_FILTER_SELECT = 'Choose a saved filter'
SAVED_FILTER_NONE = 'You have no saved filters.'
SAVED_FILTER_APPLY = 'Open filter on map'
SAVED_FILTER_DELETE = 'Delete saved filter'
SAVED_FILTER_SAVED = 'Filter saved.'
SAVED_FILTER_NAME_REQUIRED = 'Enter a name for the filter.'
SAVED_FILTER_CURRENT_FMT = 'Current filters: {0} · {1} · {2} · {3}'
REPORT_INBOX = 'Community reports'
REPORT_EMPTY = 'No reports yet.'
REPORT_STATUS = 'Report status'
REPORT_NEW = 'New'
REPORT_REVIEWED = 'Reviewed'
REPORT_RESOLVED = 'Resolved'
REPORT_MARK_REVIEWED = 'Mark reviewed'
REPORT_MARK_RESOLVED = 'Mark resolved'
REPORT_OPEN_MAP = 'Open location on map'
PORTAL_OPEN_REPORTS_FMT = '{0} open reports'

# S2: public Overview (no priority wording)
PUB_HERO_MISSION = 'Brick kiln candidates found in satellite images and shown on a map.'
PUB_HERO_SUB = 'Find the kiln candidates near your home or village.'
PUB_OV_DISTRICTS_HINT = 'Select a district name to see its kiln candidates.'
PUB_OV_OPEN_DISTRICT_FMT = 'See kiln candidates in {0}'
PUB_HOW_3_HEAD = 'Find near you'
PUB_HOW_3_BODY = 'Candidates are shown on a map, so you can look up the ones near a place.'

# FAQ section (About page)
FAQ_TITLE = 'Frequently Asked Questions'
FAQ_Q1 = 'What is Dhoa?'
FAQ_A1 = 'Dhoa is a public map of brick kiln candidates detected from satellite images in Bangladesh. It helps communities and researchers find and report kilns in their area.'
FAQ_Q2 = 'How do I find kilns near my village?'
FAQ_A2 = "Go to 'Kilns near me', type your village or district name in the search box, or tap 'Use my location' to let the app find you automatically."
FAQ_Q3 = 'What does "candidate" mean?'
FAQ_A3 = 'A candidate is a location the satellite model flagged as likely being a brick kiln.'
FAQ_Q4 = 'How do I report a kiln?'
FAQ_A4 = "In 'Kilns near me', find the kiln on the list and tap 'Report this kiln'. Fill in what you observed and submit — it goes to our review team."
FAQ_Q5 = 'What happens after I report a kiln?'
FAQ_A5 = 'Your report appears in the Inspector Portal for review. Inspectors can view its map location, download its report, and mark it reviewed or resolved.'
FAQ_Q6 = 'How do I switch to English or Bangla?'
FAQ_A6 = "Use the language toggle (EN / বাং) at the top of the page to switch between English and Bangla."
FAQ_SECTIONS = (
    ("About Dhoa", (
        ("What is Dhoa, and how does it work?", "Dhoa maps potential brick kiln locations identified from Sentinel-2 satellite imagery, adds nearby place and map context, and lets community users search candidates and submit reports."),
        ("Who can use Dhoa?", "The Overview, Kilns near me, and About views are public. The Inspector Portal requires staff sign-in."),
    )),
    ("AI Detection", (
        ("How does Dhoa identify potential brick kiln locations?", "A trained image model analyzes Sentinel-2 imagery and produces candidate locations. The map combines these results with available geographic context."),
        ("Are detected locations confirmed brick kilns?", "No. They are model-identified candidates and may include false detections. Dhoa does not confirm a site through the map alone."),
        ("How are potential kilns prioritized?", "The map ranks candidates into high, medium, and low priority bands using the configured screening signals. A priority is a review aid, not a legal finding."),
        ("Can Dhoa make mistakes or miss existing kilns?", "Yes. Image conditions, site changes, and model limitations can cause missed or incorrect candidates. The map is not a complete or field-verified inventory."),
    )),
    ("Community View", (
        ("How can I check for potential brick kilns near my community?", "Open Kilns near me, search for a place or use your location, choose a search distance, and review the candidates shown on the map and list."),
        ("How does the search radius work?", "It filters candidates by distance from the selected search point. Some named places are represented by a broader area, so a radius may not apply to every place search."),
        ("How can I report a missing brick kiln?", "The current report form is attached to listed candidates. If a kiln is missing from the list, Dhoa does not currently provide a separate map-pin report flow."),
        ("Can I report a location if I am unsure whether it is a kiln?", "Reports can share an observation about a listed candidate. State what you observed and what is uncertain; submitting a report does not confirm the location."),
    )),
    ("Inspections and Environmental Monitoring", (
        ("How can inspectors use Dhoa to plan field visits?", "Authorized inspectors can use the map, filters, priority bands, and candidate details to organize desk review and plan where to investigate."),
        ("Does detecting a kiln mean it is operating illegally?", "No. A candidate is not proof that a kiln exists, is operating, or violates a rule. Legal status requires separate evidence and assessment."),
        ("How can Dhoa support environmental monitoring?", "Candidate locations and nearby map context can help identify places for further review. Dhoa does not measure emissions or verify environmental conditions."),
        ("Where does Dhoa's data come from, and how reliable is it?", "Candidate locations come from model analysis of Sentinel-2 imagery; nearby context comes from the map datasets shown in the app. Coverage and accuracy vary, and candidates are not field-verified."),
    )),
)

# Chatbot
CHAT_PLACEHOLDER = 'Ask a question or type an area, district, upazila, or landmark…'
CHAT_TITLE = '💬 Help'
CHAT_WELCOME = 'Hi! I can help find nearby kilns. Tell me a district, upazila, or landmark, or ask me how to use Dhoa.'
CHAT_FALLBACK = 'I can look up districts, upazilas, and landmarks, or answer questions about Dhoa. Which area should I find?'
CHAT_GO_DISTRICT = 'Showing kilns in {0}. Opening the map now…'
CHAT_AREA_AMBIGUOUS = 'More than one area matches. Add its district or upazila to narrow it down: {0}.'
CHAT_SEARCH_PLACE_FMT = "I didn’t find an exact saved match for '{0}'. I’ve put it in Kilns near me; choose a location suggestion there to continue."
CHAT_GO_NEAR_ME = "Opening 'Kilns near me'…"
CHAT_GO_OVERVIEW = 'Opening the Overview map…'
CHAT_GO_ABOUT = 'Opening the About page…'
CHAT_GO_INSPECTOR = 'Opening the Inspector Portal…'
CHAT_HOW_REPORT = "Find your kiln in 'Kilns near me', then tap 'Report this kiln' on that row."
CHAT_WHAT_CANDIDATE = 'A candidate is a location the satellite model flagged as a possible brick kiln.'
CHAT_HOW_LANGUAGE = 'Use the EN / বাং toggle at the top of the page to switch language.'

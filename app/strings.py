"""All user-facing Bangla text for the Dhoa dashboard (single source).

Input schema: none (constants only). Output schema: module-level ``str`` constants;
entries containing ``{0}``-style fields are ``str.format`` templates. Text is kept in
real Bangla characters; an English gloss from the pre-M1 source is given as a comment
where one existed. Needs native-speaker review before release.
"""

from __future__ import annotations

APP_TITLE = 'ধোঁয়া'
CHANDRABINDU = 'ঁ'

# All types
ALL_TYPES = 'সব ধরন'

# Zigzag kiln
ZIGZAG_KILN = 'জিগজ্যাগ ইটভাটা'

# Fixed chimney kiln
FIXED_CHIMNEY_KILN = 'ফিক্সড চিমনি ইটভাটা'
COL_KILN_ID = 'ভাটা ID'
COL_LATITUDE = 'অক্ষাংশ'
COL_LONGITUDE = 'দ্রাঘিমাংশ'

# District
DISTRICT = 'জেলা'
COL_UPAZILA = 'উপজেলা'
COL_NEAREST_PLACE = 'নিকটতম স্থান'
COL_DISTANCE_M = 'দূরত্ব (মি)'

# Priority
PRIORITY = 'অগ্রাধিকার'
COL_BREACH_COUNT = 'লঙ্ঘন সংখ্যা'
METRIC_TOTAL_KILNS = 'মোট ভাটা'
METRIC_HIGH_PRIORITY_KILNS = 'পরিবেশ বিপজ্জনক ভাটা'
METRIC_RULE_VIOLATIONS = 'আইন লঙ্ঘন'
METRIC_LAST_UPDATED = 'সর্বশেষ হালনাগাদ'
METRIC_TOTAL_CANDIDATES = 'মোট প্রার্থী'
METRIC_ESTIMATED_AREA = 'আনুমানিক এলাকা (বর্গ কিমি)'
METRIC_PRIMARY_SIGNAL = 'প্রধান নিয়ম-সংকেত'
METRIC_NEW_CANDIDATES = 'নতুন প্রার্থী'
METRIC_RULE_SIGNALS = 'নিয়ম সংকেত'

# High
HIGH = 'উচ্চ'

# Medium
MEDIUM = 'মাঝারি'

# Low
LOW = 'নিম্ন'

# Unclassified
UNCLASSIFIED = 'নির্ধারিত নয়'

# All districts
ALL_DISTRICTS = 'সব জেলা'
DISTRICT_CHAPAINAWABGANJ = 'চাঁপাইনবাবগঞ্জ'
DISTRICT_GAZIPUR = 'গাজীপুর'
DISTRICT_RAJSHAHI = 'রাজশাহী'
DISTRICT_DHAKA = 'ঢাকা'
DISTRICT_CHITTAGONG = 'চট্টগ্রাম'

# Unknown area
UNKNOWN_AREA = 'অজানা এলাকা'

# Near school
NEAR_SCHOOL = 'স্কুলের কাছে'

# Near hospital
NEAR_HOSPITAL = 'হাসপাতালের কাছে'

# Near settlement
NEAR_SETTLEMENT = 'বসতির কাছে'

# Near railway
NEAR_RAILWAY = 'রেলপথের কাছে'

# Near wetland
NEAR_WETLAND = 'জলাভূমির কাছে'

# Near government forest
NEAR_GOVERNMENT_FOREST = 'সরকারি বনের কাছে'

# Fixed chimney technology
FIXED_CHIMNEY_TECHNOLOGY = 'ফিক্সড চিমনি প্রযুক্তি'

# school
SCHOOL = 'স্কুল'

# hospital
HOSPITAL = 'হাসপাতাল'

# settlement
SETTLEMENT = 'বসতি'

# railway
RAILWAY = 'রেলপথ'

# wetland
WETLAND = 'জলাভূমি'

# government forest
GOVERNMENT_FOREST = 'সরকারি বন'

# No rule signals recorded
NO_RULE_SIGNALS_RECORDED = 'কোনো নিয়ম-সংকেত নথিভুক্ত নেই'

# Street map
STREET_MAP = 'রাস্তার মানচিত্র'

# Satellite imagery
SATELLITE_IMAGERY = 'স্যাটেলাইট ছবি'

# Map type
MAP_TYPE = 'মানচিত্রের ধরন'
REPORT_COMMUNITY_NOTE = 'এই প্রতিবেদনটি কমিউনিটি সচেতনতার জন্য — শুধুমাত্র তথ্যের উদ্দেশ্যে।'

# My location
MY_LOCATION = 'আমার অবস্থান'

# Find kilns near you
FIND_KILNS_NEAR_YOU = 'আপনার এলাকার কাছাছি খুঁজুন'

# 🔊 Listen to the guide
LISTEN_TO_THE_GUIDE = '🔊 ব্যবহার নির্দেশিকা শুনুন'

# 🔊 Audio guide coming soon
AUDIO_GUIDE_COMING_SOON = '🔊 অডিও নির্দেশিকা শীঘ্রই আসছে'

# Area / Thana
AREA_THANA = 'এলাকা (উপজেলা)'

# Search radius (metres)
SEARCH_RADIUS_METRES = 'অনুসন্ধানের ব্যাসার্ধ (মিটার)'

# Search by name
SEARCH_BY_NAME = 'নাম লিখুন'

# e.g. Ashulia
E_G_ASHULIA = 'যেমন: আশুলি'

# 🔍 Search
SEARCH = '🔍 অনুসন্ধান করুন'

# **Or use your current location:**
OR_USE_YOUR_CURRENT_LOCATION = '**অথবা আপনার বর্তমান অবস্থান ব্যবহার করুন:**'

# Use my location
USE_MY_LOCATION = 'আমার অবস্থান ব্যবহার করুন'

# Your location
YOUR_LOCATION = 'আপনার অবস্থান'

# ⚠️ Please enter a location name.
PLEASE_ENTER_A_LOCATION_NAME = '⚠️ খোঁজার জন্য একটি এলাকার নাম লিখুন।'

# Searching…
SEARCHING = 'খোঁজা হচ্ছে…'

# ⚠️ Location not found. Try a different spelling or add the district, e.g. 'Ashulia, Savar'.
LOCATION_NOT_FOUND_TRY_A_DIFFERENT_SPELL = "⚠️ স্থানের নাম পাওয়া যায়নি। অন্য বানান বা 'Ashulia, Savar' এর মতো লিখুন।"

# Select a district and search for a place or use GPS to view kilns.
SELECT_A_DISTRICT_AND_SEARCH_FOR_A_PLACE = 'ভাটা দেখতে একটি জেলা নির্বাচন করুন।'

# Nearby kiln candidates
NEARBY_KILN_CANDIDATES = 'কাছাকাছির ইটভাটার প্রার্থী'

# Download report
DOWNLOAD_REPORT = 'প্রতিবেদন ডাউনলোড করুন'

# Report generation failed. Please try again.
REPORT_GENERATION_FAILED_PLEASE_TRY_AGAI = 'প্রতিবেদন তৈরি করা যায়নি। আবার চেষ্টা করুন।'

# Distance (m)
DISTANCE_M = 'দূরত্ব (মিটার)'

# Area
AREA = 'এলাকা'

# Kiln type
KILN_TYPE = 'ভাটার ধরন'

# Directions
DIRECTIONS = 'দিকনির্দেশনা'

# No data
NO_DATA = 'তথ্য নেই'

# Get directions
GET_DIRECTIONS = 'দিকনির্দেশনা পান'

# Download community CSV
DOWNLOAD_COMMUNITY_CSV = 'কমিউনিটি তালিকা ডাউনলোড করুন'

# Area map
AREA_MAP = 'এলাকার মানচিত্র'
SEARCH_POINT_LABEL = 'খোঁজার স্থান'
AREA_CENTROID_LABEL = 'নির্বাচিত এলাকার কেন্দ্রবিন্দু'

# High priority
HIGH_PRIORITY = 'উচ্চ অগ্রাধিকার'

# forest
FOREST = 'বন'

# 🌲 Forest data unavailable
FOREST_DATA_UNAVAILABLE = '🌲 বনের তথ্য মানচিত্রে নেই'

# Outside threshold
OUTSIDE_THRESHOLD = 'সীমার বাইরে'

# New candidate (2025-26)
NEW_CANDIDATE_2025_26 = 'নতুন (২০২৫–২৬)'

# Previously detected (2023-24)
PREVIOUSLY_DETECTED_2023_24 = 'আগে চিহ্নিত (২০২৩–২৪)'
NEW_SUFFIX = ' [নতুন]'
RULE_SIGNALS_HEADING = 'নিয়মের সংকেত:'
POPUP_LINKS = '[🗺️ দিকনির্দেশনা] [📍 মানচিত্র] [🌍 পৃথিবী]'

# Kiln candidate
KILN_CANDIDATE = 'ইটভাটার প্রার্থী'

# Rule signals
RULE_SIGNALS = 'নিয়মের সংকেত'

# Map
MAP = 'মানচিত্র'

# Report ID
REPORT_ID = 'প্রতিবেদন নম্বর'

# View kiln
VIEW_KILN = 'ভাটাটি দেখুন'

# Bangladesh Brick Kiln Monitoring Dashboard
BANGLADESH_BRICK_KILN_MONITORING_DASHBOA = 'বাংলাদেশের ইটভাটা পর্যবেক্ষণ ড্যাশবোর্ড'

# Choose view
CHOOSE_VIEW = 'ভিউ বাছাই করুন'
VIEW_INSPECTOR = '🏛 পরিদর্শক ভিউ'
VIEW_COMMUNITY = '🏘 কমিউনিটি ভিউ'

# ❔ How to use
HOW_TO_USE = '❔ কীভাবে ব্যবহার করবেন?'
HELP_COMMUNITY = """
**কমিউনিটি ভিউ ব্যবহার**

1. **জেলা** বাছুন, চাইলে **এলাকা (উপজেলা)** বাছুন. চাইলে নামের ঘরে একটি স্থানের নাম লিখুন, অথবা ফাঁকা রেখে বাছা এলাকার কেন্দ্রবিন্দু থেকে ফলাফল দেখুন.
2. নাম দিয়ে খুঁজলে খোঁজা স্থান থেকে, অন্যথা এলাকার কেন্দ্রবিন্দু থেকে নির্বাচিত ব্যাসার্ধের ভিতরে ভাটাগুলো দেখুন.
3. ফলাফল, তালিকা ও মানচিত্র থেকে ভাটা বাছুন এবং প্রতিবেদন ডাউনলোড করুন.
"""
HELP_INSPECTOR = """
**পরিদর্শক ভিউ কীভাবে ব্যবহার করবেন**

১. বামের **ফিল্টার** খুলে জেলা, এলাকা, ইটভাটার ধরন, অগ্রাধিকার অথবা নিয়মের সংকেত বাছুন।

২. **অগ্রাধিকারের তালিকা** থেকে ইটভাটা বাছুন, অথবা মানচিত্রের চিহ্নে চাপ দিয়ে তা নির্বাচন করুন। নির্বাচিত ইটভাটার তথ্য দেখতে পাবেন।

৩. মানচিত্রে **রাস্তার মানচিত্র** অথবা **স্যাটেলাইট ছবি** বাছুন। প্রয়োজনে সিএসভি তালিকা অথবা নির্বাচিত ইটভাটার পিডিএফ প্রতিবেদন ডাউনলোড করুন।
"""

# Choose a district and upazila. You may enter a place name, or leave it blank to search around the selected area's centroid.
CHOOSE_A_DISTRICT_AND_UPAZILA_YOU_MAY_EN = 'জেলা ও চাইলে এলাকা (উপজেলা) বাছুন। চাইলে কোনো স্থানের নাম লিখুন; না লিখলে নির্বাচিত এলাকার কেন্দ্রবিন্দুকে কেন্দ্র করে ফলাফল দেখুন।'

# Browse the kiln list and map, use filters to find candidates.
BROWSE_THE_KILN_LIST_AND_MAP_USE_FILTERS = 'সুসজ্জিত ভাটাটির তালিকা ও মানচিত্র দেখুন, ফিল্টার দিয়ে প্রার্থী খুঁজুন।'

# None
NONE = 'নেই'
RISK_SCOPE_SCHOOLS_HOSPITALS = 'স্কুল ও হাসপাতালের কাছে'
RISK_SCOPE_SIGNALS = 'নিয়ম-সংকেতযুক্ত'

# Search
SEARCH_2 = 'অনুসন্ধান'

# All areas
ALL_AREAS = 'সব এলাকা'

# Search radius
SEARCH_RADIUS = 'অনুসন্ধান ব্যাসার্ধ'

# Select an upazila to enable the radius
SELECT_AN_UPAZILA_TO_ENABLE_THE_RADIUS = 'উপজেলা নির্বাচন করলে ব্যাসার্ধ সক্রিয় হবে'

# Filters
FILTERS = 'ফিল্টার'

# ⬇ Download filtered CSV
DOWNLOAD_FILTERED_CSV = '⬇ বাছাইকৃত তালিকা সিএসভি ডাউনলোড'

# Department of Environment hotline: 16131 | [doe.gov.bd](https://doe.gov.bd)
DEPARTMENT_OF_ENVIRONMENT_HOTLINE_16131_ = 'পরিবেশ অধিদপ্তরের হটলাইন: ১৬১৩১ | [doe.gov.bd](https://doe.gov.bd)'

# 🔄 Reset filters
RESET_FILTERS = '🔄 ফিল্টার রিসেট করুন'
APPLY_FILTERS = 'ফিল্টার প্রয়োগ করুন'  # Apply filters (needs native-speaker review)

# Distance from government forest
DISTANCE_FROM_GOVERNMENT_FOREST = 'সরকারি বন থেকে দূরত্ব'

# Kiln type
KILN_TYPE_2 = 'ধরন'
STATUS_NEW = 'নতুন প্রার্থী (২০২৫–২৬)'
STATUS_KNOWN = 'আগে চিহ্নিত (২০২৩–২৪ জরিপ)'

# Detection status
DETECTION_STATUS = 'শনাক্তকরণের অবস্থা'

# Coordinates
COORDINATES = 'স্থানাঙ্ক'

# 🗺️ Directions
DIRECTIONS_2 = '🗺️ দিকনির্দেশনা'

# 📍 Street view
STREET_VIEW = '📍 রাস্তার দৃশ্য'

# 🌍 Google Earth
GOOGLE_EARTH = '🌍 পৃথিবী'

# Could not generate the report. Please try again.
COULD_NOT_GENERATE_THE_REPORT_PLEASE_TRY = '❌ প্রতিবেদন তৈরি করা যায়নি। আবার চেষ্টা করুন।'

# 📄 Download selected kiln PDF
DOWNLOAD_SELECTED_KILN_PDF = '📄 নির্বাচিত প্রার্থীর পিডিএফ ডাউনলোড'

# Could not generate the report.
COULD_NOT_GENERATE_THE_REPORT = 'প্রতিবেদন তৈরি করা যায়নি।'

# ✓ Selected
SELECTED = '✓ নির্বাচিত'

# 🔥 Priority list
PRIORITY_LIST = '🔥 অগ্রাধিকার তালিকা'

# No candidates match these filters.
NO_CANDIDATES_MATCH_THESE_FILTERS = 'এই ফিল্টারে কোনো প্রার্থী নেই।'

# Marker colour shows priority; bold border shows the selected candidate.
MARKER_COLOUR_SHOWS_PRIORITY_BOLD_BORDER = 'চিহ্নের আকার ও রং অগ্রাধিকার বোঝায় (▲ উচ্চ, ◆ মাঝারি, ● নিম্ন); গাঢ় বৃত্ত নির্বাচিত প্রার্থীকে দেখায়।'

# Select a candidate from the list or map to generate a PDF report.
SELECT_A_CANDIDATE_FROM_THE_LIST_OR_MAP_ = 'পিডিএফ পেতে তালিকা বা মানচিত্র থেকে একটি প্রার্থী নির্বাচন করুন।'

# Could not render the map.
COULD_NOT_RENDER_THE_MAP = 'মানচিত্র তৈরি করা যায়নি।'

# Tap any kiln marker on the map to view details and generate a report.
TAP_ANY_KILN_MARKER_ON_THE_MAP_TO_VIEW_D = 'বিস্তারিত ও প্রতিবেদন দেখতে মানচিত্রের কোনো ইটভাটার চিহ্নে চাপ দিন।'

# Clear kiln selection · Show all kilns
CLEAR_KILN_SELECTION_SHOW_ALL_KILNS = 'ভাটার নির্বাচন বাতিল করুন · সব ভাটা দেখুন'
HOTLINE_LABEL = 'ধোঁয়া · DoE হটলাইন'

# Loading kiln data. This may take a few seconds…
LOADING_KILN_DATA_THIS_MAY_TAKE_A_FEW_SE = 'ডেটা লোড হচ্ছে। কয়েক সেকেন্ড সময় লাগতে পারে…'

# Could not load dashboard data. Please try again later.
COULD_NOT_LOAD_DASHBOARD_DATA_PLEASE_TRY = '❌ তথ্য বা ড্যাশবোর্ড লোড করা যায়নি। দয়া করে পরে চেষ্টা করুন।'

# Retry loading data
RETRY_LOADING_DATA = 'আবার চেষ্টা করুন'

# Dashboard data is unavailable.
DASHBOARD_DATA_IS_UNAVAILABLE = '❌ ড্যাশবোর্ডের তথ্য পাওয়া যাচ্ছে না। প্রথমে ডেটা প্রসেস করে নিন।'

# ⚖️ Relevant law — Brick Manufacturing and Kiln Establishment (Control) Act, 2013
RELEVANT_LAW_BRICK_MANUFACTURING_AND_KIL = '⚖️ প্রাসঙ্গিক আইন — ইট প্রস্তুত ও ভাটা স্থাপন (নিয়ন্ত্রণ) আইন, ২০১৩'
LAW_TEXT = """
**ধারা ৮(১)** — নিষিদ্ধ এলাকায় ইটভাটা স্থাপন করা যাবে না:
- আবাসিক এলাকা (কমপক্ষে ৫০টি পরিবার)
- সিটি কর্পোরেশন, পৌরসভা বা উপজেলা সদর
- সরকারি বা ব্যক্তিমালিকানাধীন বন, অভয়ারণ্য, জলাভূমি
- কৃষি জমি
- প্রতিবেশগত সংকটাপন্ন এলাকা
- ডিগ্রেডেড এয়ার শেড

**ধারা ৮(৩)** — নিম্নবর্ণিত দূরত্বের মধ্যে ইটভাটা নিষিদ্ধ:
- নিষিদ্ধ এলাকার সীমা থেকে **১ কিলোমিটার**
- সরকারি বনাঞ্চল থেকে **২ কিলোমিটার**
- পাহাড়ের পাদদেশ থেকে **০.৫ কিলোমিটার**
- শিক্ষা প্রতিষ্ঠান, হাসপাতাল, রেলপথ থেকে **১ কিলোমিটার**

*সূত্র: ইট প্রস্তুত ও ভাটা স্থাপন (নিয়ন্ত্রণ) আইন, ২০১৩ (সংশোধিত ২০১৯)*
                """

# Could not render the dashboard.
COULD_NOT_RENDER_THE_DASHBOARD = '❌ ড্যাশবোর্ড দেখানো যায়নি।'
SUBTITLE_UPDATED_FMT = ' · তথ্য হালনাগাদ {0}'
RISK_INFO_FMT = '{0} জেলায় {1} {2}টি উচ্চ অগ্রাধিকারপ্রাপ্ত প্রার্থী পাওয়া গেছে।'
SELECTED_KILN_TITLE_FMT = '✅ নির্বাচিত প্রার্থী · ইটভাটা #{0}'
CENTROID_OF_AREA_FMT = 'নির্বাচিত এলাকা {0} কেন্দ্রবিন্দু'
POPUP_TITLE_FMT = 'ইটভাটার প্রার্থী · {0}'
POPUP_PRIORITY_FMT = 'অগ্রাধিকার: {0}'
POPUP_AREA_FMT = '📍 এলাকা: {0}'
POPUP_REPORT_ID_FMT = '[📄 প্রতিবেদন নম্বর: {0}]'
DISTANCE_FROM_FMT = '{0} থেকে দূরত্ব'
NO_KILNS_IN_AREA_FMT = "'{0}' এলাকায় কোনো ভাটার তথ্য পাওয়া যায়নি।"

COORDS_FMT = '{0:.5f}° উত্তর, {1:.5f}° পূর্ব'
KM_FMT = '{0:.1f} কিমি'
M_FMT = '{0:,.0f} মি'
METRES_FMT = '{0:,.0f} মিটার'
COMMUNITY_MAP_CAPTION_FMT = 'নীল বৃত্তের সীমানা {0} থেকে {1:g} কিমি দূরত্ব দেখায়। লাল, কমলা ও সবুজ বিন্দু ভাটার অগ্রাধিকার দেখায়; বিন্দুতে চাপলে বিস্তারিত দেখুন।'
M_DOT_FMT = '{0:,.0f} মি.'
CANDIDATES_MATCH_FMT = '{0:,}টি ফিল্টারের সাথে মেলা প্রার্থী'
REASON_FROM_FMT = '{0} থেকে {1:,.0f} মিটার'
NO_KILNS_IN_RADIUS_FMT = '✅ {0:g} কিমি ব্যাসার্ধে কোনো ভাটা পাওয়া যায়নি।'
KILNS_WITHIN_RADIUS_FMT = '{0:g} কিমি ব্যাসার্ধের মধ্যে ভাটা'
PAGE_LOADING = 'পৃষ্ঠা লোড হচ্ছে, অপেক্ষা করুন…'

# --- M4 Inspector redesign (native-speaker review needed for the new copy) ---
RAIL_HINT = 'ফিল্টার বেছে নিয়ে “ফিল্টার প্রয়োগ করুন” চাপুন।'
SUMMARY_MATCHING = 'মেলা প্রার্থী'
SUMMARY_HIGH = 'উচ্চ অগ্রাধিকার'
SUMMARY_MEDIUM = 'মাঝারি অগ্রাধিকার'
SUMMARY_LOW = 'নিম্ন অগ্রাধিকার'
SUMMARY_NEW = 'নতুন প্রার্থী'
PRIORITY_NOTE = (
    'উচ্চ, মাঝারি ও নিম্ন অগ্রাধিকার হলো সব প্রার্থীর র\u200d্যাংকিংয়ের আপেক্ষিক ভাগ '
    '(শীর্ষ ২০%, পরের ৪০%, বাকি ৪০%)। এটি ঝুঁকির পরম মাত্রা নয়।'
)
PRIORITY_LEGEND = 'চিহ্ন'
EMPTY_FILTER_HINT = 'ফিল্টার বদলে আবার চেষ্টা করুন, অথবা সব ফিল্টার মুছে দিন।'
LOADING_MAP = 'মানচিত্র তৈরি হচ্ছে…'
RETRY = '🔄 আবার চেষ্টা করুন'
DETAIL_HINT = 'তালিকা থেকে একটি প্রার্থী বেছে নিন, অথবা মানচিত্রে চিহ্নে ক্লিক করুন।'

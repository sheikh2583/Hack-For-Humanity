"""Bangla catalogue for the Dhoa dashboard (read through ``strings``; do not import directly).

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
COL_BREACH_COUNT = 'নিয়মের সংকেতের সংখ্যা'
METRIC_TOTAL_KILNS = 'মোট ভাটা'
METRIC_HIGH_PRIORITY_KILNS = 'উচ্চ অগ্রাধিকার প্রার্থী'
METRIC_RULE_VIOLATIONS = 'নিয়মের সংকেত'
METRIC_LAST_UPDATED = 'তথ্য যে তারিখ পর্যন্ত'
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
VIEW_INSPECTOR = '🔒 পরিদর্শক পোর্টাল'
VIEW_COMMUNITY = 'আমার কাছের ভাটা'

# ❔ How to use
HOW_TO_USE = 'সহায়তা'
HELP_COMMUNITY = """
**“আমার কাছের ভাটা” ব্যবহার**

১. অনুসন্ধান বাক্সে জেলা, উপজেলা বা কাছের কোনো স্থানের নাম লিখুন।

২. **মিল থাকা এলাকা** তালিকা থেকে সঠিক স্থানটি বেছে নিন।

৩. বিকল্পভাবে **আমার অবস্থান ব্যবহার করুন** বেছে নিয়ে ব্রাউজারে অবস্থান ব্যবহারের অনুমতি দিন।

৪. কোনো নামযুক্ত এলাকা বেছে নিলে সেই এলাকার সব ইটভাটার প্রার্থী দেখানো হয়, তাই দূরত্ব বাছাই করার দরকার নেই।

৫. বর্তমান অবস্থান ব্যবহার করলে **১ কিমি**, **২ কিমি**, **৫ কিমি** অথবা **১০ কিমি** বেছে নিন।

৬. মানচিত্রে ইটভাটার প্রার্থীগুলো দেখুন এবং কোনো চিহ্ন বেছে নিয়ে পাওয়া তথ্য দেখুন।

৭. কোনো ইটভাটা না থাকলে জানাতে **মানচিত্রে নেই এমন ভাটা জানান** খুলুন।

৮. অক্ষাংশ ও দ্রাঘিমাংশ লিখুন, একটি ছোট নোট যোগ করুন এবং চাইলে যোগাযোগের তথ্য ও একটি ছবি যোগ করুন।

৯. এগুলো পর্যবেক্ষণ ও মাঠপর্যায়ে যাচাইয়ের জন্য স্যাটেলাইট-ভিত্তিক ইটভাটার প্রার্থী; এগুলো চূড়ান্ত আইনি বা প্রয়োগমূলক সিদ্ধান্ত নয়।

[▶ Play voice guide — audio coming soon]
"""
HELP_INSPECTOR = """
**পরিদর্শক পোর্টাল**

১. **ড্যাশবোর্ড:** মোট প্রার্থী, উচ্চ অগ্রাধিকার প্রার্থী, জেলার সারাংশ এবং সবচেয়ে বেশি প্রার্থী থাকা উপজেলাগুলো দেখুন।

২. **মানচিত্র:** জেলা, এলাকা/উপজেলা, অগ্রাধিকার এবং ইটভাটার ধরন দিয়ে বাছাই করুন। বাছাই ব্যবহার করতে **বাছাই প্রয়োগ করুন** এবং মুছে ফেলতে **বাছাই রিসেট করুন** বেছে নিন। অবস্থান বোঝার জন্য **রাস্তার মানচিত্র** ও ঘনত্বের হিটম্যাপ ব্যবহার করুন এবং **বাছাই করা তালিকা ডাউনলোড করুন (CSV)** দিয়ে বাছাই করা তালিকা ডাউনলোড করুন।

৩. **ভাটাটি দেখুন:** একটি প্রার্থী খুলে তার তথ্য পর্যালোচনা করুন। পাওয়া যায় এমন কাজগুলো হলো **পিডিএফ ডাউনলোড করুন**, **মানচিত্রে অবস্থান খুলুন**, **দিকনির্দেশ**, **রাস্তার দৃশ্য**, **Google Earth**, **পরিদর্শনের অবস্থা হালনাগাদ করুন**, **আমাকে বরাদ্দ করুন** অথবা পরিদর্শনটি বরাদ্দ করুন, **নোট যোগ করুন**, এবং **পরিদর্শনের ছবি সংযুক্ত করুন**। শেষ হলে **হালনাগাদ সংরক্ষণ করুন** বেছে নিন।

৪. **কাজ:** বরাদ্দ করা পরিদর্শন, সংরক্ষিত বাছাই, পরিদর্শনের অবস্থা, অগ্রাধিকার, দূরত্ব, রুট, মানচিত্রের রুট এবং দিকনির্দেশনা পরিচালনা করুন।

৫. **প্রতিবেদন:** কমিউনিটি প্রতিবেদন ও নিয়মের সংকেত পর্যালোচনা করুন, অবস্থান খুলুন, **পর্যালোচিত হিসেবে চিহ্নিত করুন** বা **সমাধান হিসেবে চিহ্নিত করুন** বেছে নিন এবং প্রতিবেদন ডাউনলোড করুন।

৬. কাজ শেষ হলে, বিশেষ করে শেয়ার করা কম্পিউটারে, **বের হয়ে যান**।

৭. মানচিত্রের শনাক্তকরণ, দূরত্বের নির্দেশক এবং অগ্রাধিকার স্তর মাঠপর্যায়ে যাচাইয়ে সহায়তা করে; এগুলো চূড়ান্ত প্রয়োগমূলক সিদ্ধান্ত নয়।

[▶ Play voice guide — audio coming soon]
"""

# Choose a district and upazila. You may enter a place name, or leave it blank to search around the selected area's centroid.
CHOOSE_A_DISTRICT_AND_UPAZILA_YOU_MAY_EN = 'তিনটি ধাপে আপনার এলাকার কাছের ভাটার প্রার্থী দেখুন।'

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
FILTER_DISTRICT_HINT = 'এলাকার তালিকা ছোট করতে একটি জেলা বেছে নিন।'

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

# Could not render the dashboard.
COULD_NOT_RENDER_THE_DASHBOARD = '❌ ড্যাশবোর্ড দেখানো যায়নি।'
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


# --- M5 Community redesign (native-speaker review needed for ALL copy below) ---
C_STEP1 = '১. কোথায় খুঁজবেন?'
C_PLACE_LABEL = 'আপনার এলাকা খুঁজুন'
C_PLACE_PLACEHOLDER = 'এলাকার নাম লিখুন (যেমন: Savar)'
C_PLACE_HELP = 'এলাকা খুঁজতে কয়েকটি অক্ষর লিখুন, অথবা স্থানের নাম লিখে Enter চাপুন।'
C_PLACE_SUGGESTIONS = 'মিল থাকা এলাকা'
C_PLACE_SUGGESTION_PLACEHOLDER = 'মিল থাকা এলাকা বেছে নিন'
C_GEO_SUGGESTION_FMT = 'বাংলাদেশে “{0}” খুঁজুন'
C_PLACE_LABEL_FMT = '{name} · {count}টি ভাটা'
C_GPS_LABEL = '📍 আমার অবস্থান ব্যবহার করুন'
C_GPS_BUSY = 'অবস্থান খোঁজা হচ্ছে…'
C_GPS_OK = 'আপনার অবস্থান পাওয়া গেছে।'
C_GPS_DENIED = 'অবস্থানের অনুমতি দেওয়া হয়নি। ব্রাউজারের সেটিংসে অনুমতি দিন, অথবা ওপরে আপনার এলাকা খুঁজুন।'
C_GPS_UNSUPPORTED = 'এই ব্রাউজারে অবস্থান জানা যায় না। ওপরে আপনার এলাকা খুঁজুন।'
C_GPS_INSECURE = 'নিরাপদ সংযোগ (https) ছাড়া অবস্থান জানা যায় না। ওপরে আপনার এলাকা খুঁজুন।'
C_GPS_UNAVAILABLE = 'আপনার অবস্থান জানা গেল না। ওপরে আপনার এলাকা খুঁজুন।'
C_GPS_TIMEOUT = 'অবস্থান পেতে বেশি সময় লাগছে। আবার চেষ্টা করুন, অথবা আপনার এলাকা খুঁজুন।'
C_GPS_HINT = 'ব্রাউজার অবস্থানের অনুমতি চাইবে। অনুমতি না দিলে ওপরের অনুসন্ধান বাক্স ব্যবহার করুন।'
C_GEO_EMPTY = 'খোঁজার জন্য একটি নাম লিখুন।'
C_GEO_SEARCHING = 'জায়গা খোঁজা হচ্ছে…'
C_GEO_NOT_FOUND = 'এই নামে বাংলাদেশে কোনো জায়গা পাওয়া যায়নি। অন্য বানানে লিখুন, অথবা ওপরে আওতাভুক্ত এলাকা খুঁজুন।'
C_GEO_UNAVAILABLE = 'এই মুহূর্তে নাম দিয়ে খোঁজা যাচ্ছে না। ওপরে আওতাভুক্ত এলাকা খুঁজুন, অথবা কিছুক্ষণ পরে আবার চেষ্টা করুন।'
C_OUTSIDE_FMT = '“{0}” আমাদের তথ্যের আওতাভুক্ত জেলাগুলোর বাইরে। আওতাভুক্ত জেলা: {1}। এসব জেলার কোনো জায়গা বেছে নিন।'
C_STEP2 = '২. কত দূর পর্যন্ত?'
C_RADIUS_LABEL = 'দূরত্ব'
C_RADIUS_OPTION_FMT = '{0:g} কিমি'
C_RADIUS_HELP = 'বাছাই করা জায়গা থেকে এই দূরত্বের মধ্যের ভাটা দেখানো হবে।'
C_RADIUS_AREA_NOTE = 'পুরো এলাকার সব ভাটা দেখানো হচ্ছে, তাই দূরত্ব বাছতে হবে না।'
C_STEP3 = '৩. ফলাফল'
C_PICK_PROMPT = 'শুরু করতে ওপরে আপনার এলাকা খুঁজুন, অথবা “আমার অবস্থান ব্যবহার করুন” চাপুন।'
C_SUMMARY_RADIUS_FMT = '{1} থেকে {0:g} কিমির মধ্যে {2:,}টি ভাটা'
C_SUMMARY_AREA_FMT = '{0} এলাকায় {1:,}টি ভাটা'
C_SUMMARY_HIGH_FMT = 'এর মধ্যে {0:,}টি উচ্চ অগ্রাধিকার'
C_EMPTY_NEAREST_FMT = '{0:g} কিমির মধ্যে কোনো ভাটা পাওয়া যায়নি। সবচেয়ে কাছের ভাটা {1:.1f} কিমি দূরে ({2})।'
C_EMPTY_FAR_FMT = '{0:g} কিমির মধ্যে কোনো ভাটা পাওয়া যায়নি। সবচেয়ে কাছের ভাটা {1:.1f} কিমি দূরে ({2}), যা বাছাইযোগ্য সর্বোচ্চ দূরত্বের বাইরে।'
C_EMPTY_NONE = 'এখানে কোনো ভাটার তথ্য পাওয়া যায়নি। অন্য জায়গা বেছে নিন।'
C_SHOW_WITHIN_FMT = '{0:g} কিমির মধ্যে দেখুন'
C_LIST_TITLE = 'কাছাকাছি ভাটার তালিকা'
C_CARD_DISTANCE_FMT = 'দূরত্ব: {0}'
C_CARD_PLACE_FMT = 'নিকটতম স্থান: {0}'
C_REPORT_EXISTING_TITLE = 'এই ভাটাটি রিপোর্ট করুন'
C_REPORT_CARD_ACTION = 'এই ভাটাটি রিপোর্ট করুন'
C_REPORT_EXISTING_REASON = 'কী সমস্যা?'
C_REPORT_REASON_LOCATION = 'অবস্থান ভুল'
C_REPORT_REASON_NOT_KILN = 'এটি ইটভাটা নয়'
C_REPORT_REASON_CONCERN = 'সম্ভাব্য পরিবেশগত বা অবস্থানগত সমস্যা'
C_REPORT_REASON_OTHER = 'অন্য সমস্যা'
C_REPORT_NEW_TITLE = 'মানচিত্রে নেই এমন ভাটা জানান'
C_REPORT_LAT = 'অক্ষাংশ'
C_REPORT_LON = 'দ্রাঘিমাংশ'
C_REPORT_NOTE = 'সংক্ষিপ্ত নোট'
C_REPORT_CONTACT = 'যোগাযোগের তথ্য (ঐচ্ছিক)'
C_REPORT_PHOTO = 'ছবি (ঐচ্ছিক)'
C_REPORT_SUBMIT = 'প্রতিবেদন জমা দিন'
C_REPORT_SENT = 'আপনার প্রতিবেদন জমা হয়েছে। ধন্যবাদ।'
C_REPORT_SUCCESS_BUTTON = 'সফলভাবে রিপোর্ট করা হয়েছে'
C_REPORT_INVALID_COORDS = 'দেওয়া স্থানটি আমাদের তথ্যের আওতার মধ্যে পড়েনি। মানচিত্রে থাকা এলাকার স্থানাঙ্ক দিন।'
C_REPORT_COORDS_HELP = 'স্থানাঙ্ক মানচিত্রে থাকা এলাকার সীমার মধ্যে হতে হবে।'
C_REPORT_NO_EXTENT = 'এই মুহূর্তে প্রতিবেদনের জন্য এলাকার তথ্য পাওয়া যাচ্ছে না।'
C_REPORT_RATE_LIMIT = 'অল্প সময়ের মধ্যে অনেক প্রতিবেদন জমা হয়েছে। কিছুক্ষণ পরে আবার চেষ্টা করুন।'
C_REPORT_FAILED = 'প্রতিবেদন জমা দেওয়া যায়নি। আবার চেষ্টা করুন।'
C_REPORT_PRIVACY = 'এই প্রতিবেদনের সঙ্গে দেওয়া স্থান, কারণ, নোট, জমা দেওয়ার সময় এবং ঐচ্ছিক যোগাযোগের তথ্য বা ছবি সংরক্ষণ করা হবে। আপনার সম্পর্কে অন্য কোনো তথ্য সংগ্রহ করা হয় না।'
C_REPORT_HONEYPOT = 'ওয়েবসাইট'
C_MAP_CAPTION_RADIUS_FMT = 'নীল বৃত্তের সীমানা {0} থেকে {1:g} কিমি দূরত্ব দেখায়। প্রতিটি চিহ্ন একটি ভাটা; চিহ্নে চাপলে বিস্তারিত দেখুন।'
C_MAP_CAPTION_AREA_FMT = 'মানচিত্রে {0} এলাকার সব ভাটা দেখানো হচ্ছে। প্রতিটি চিহ্ন একটি ভাটা; চিহ্নে চাপলে বিস্তারিত দেখুন।'

# P2: landing hero and top navigation (flag for native-speaker review)
NAV_OVERVIEW = 'সারসংক্ষেপ'
NAV_MAP = 'মানচিত্র'
NAV_NEAR_ME = 'আমার কাছের ভাটা'
NAV_ABOUT = 'সম্পর্কে'
HERO_MISSION = 'স্যাটেলাইট ছবি থেকে শনাক্ত করা ইটভাটা, মানচিত্রে দেখানো এবং অগ্রাধিকার অনুযায়ী সাজানো।'
HERO_SUB = 'মানচিত্রে সব প্রার্থী দেখুন, অথবা আপনার বাড়ির কাছের ভাটাগুলো খুঁজে নিন।'
HERO_CTA_MAP = 'মানচিত্র দেখুন'
HERO_CTA_NEAR_ME = 'আমার কাছের ভাটা খুঁজুন'
HERO_METRIC_DISTRICTS = 'আওতাভুক্ত জেলা'
ABOUT_TITLE = 'ধোঁয়া সম্পর্কে'
ABOUT_BODY = (
    'ধোঁয়া Sentinel-2 স্যাটেলাইট ছবিতে শনাক্ত করা ইটভাটার প্রার্থী খুঁজে দেখতে সাহায্য করে। '
    'মানচিত্রে কাছের চিহ্নিত স্থানও দেখা যায়।'
)

# P3: overview charts and district comparison (flag for native-speaker review)
OV_DISTRICTS_TITLE = 'জেলা অনুযায়ী ভাটার প্রার্থী'
OV_DISTRICTS_HINT = 'জেলার নামে চাপলে সেই জেলা মানচিত্রে খুলবে।'
OV_OPEN_DISTRICT_FMT = '{0} মানচিত্রে দেখুন'
OV_SERIES_TOTAL = 'সব প্রার্থী'
OV_SERIES_HIGH = 'উচ্চ অগ্রাধিকার'
OV_UPAZILAS_TITLE = 'সবচেয়ে বেশি প্রার্থীর উপজেলা'
OV_COL_CANDIDATES = 'প্রার্থী'
OV_COL_HIGH = 'উচ্চ অগ্রাধিকার'
OV_TYPES_TITLE = 'ভাটার ধরন'
OV_TYPE_OTHER = 'অন্যান্য বা অজানা'
OV_SHARE_FMT = '{0:.0f}%'
OV_NO_DATA = 'দেখানোর মতো তথ্য নেই।'

# --- P4: inspector ---
LEGEND_TITLE = 'মার্কারের চিহ্ন'
HEAT_TOGGLE = 'ঘনত্বের হিটম্যাপ দেখান'
HEAT_HELP = 'যেখানে অনেক ভাটা কাছাকাছি আছে সেই এলাকা গাঢ় দেখায়। এটি ঝুঁকি দেখায় না।'
DETAIL_DISTANCES_TITLE = 'কাছাকাছি স্থানের দূরত্ব'
DETAIL_WITHIN_FMT = '{0}-এর মধ্যে'
DETAIL_BEYOND_FMT = '{0}-এর বাইরে'
DETAIL_STATE_UNKNOWN = 'তথ্য নেই'

# --- P7: trust, states, About ---
HOTLINE_LINE_FMT = 'পরিবেশ অধিদপ্তরের হটলাইন: {0}'
DOE_WEB_LINE = 'পরিবেশ অধিদপ্তর: [doe.gov.bd](https://doe.gov.bd)'
FOOTER_WEB_LABEL = 'পরিবেশ অধিদপ্তর: doe.gov.bd'
CONTACT_CALL = 'কল করুন'
CONTACT_SMS = 'এসএমএস'
HOW_TITLE = 'এটি কীভাবে কাজ করে'
HOW_1_HEAD = 'স্যাটেলাইট ছবি'
HOW_1_BODY = 'পাঁচটি জেলার একটি শুষ্ক মৌসুমের সেন্টিনেল-২ ছবি সংগ্রহ করা হয়।'
HOW_2_HEAD = 'শনাক্তকরণ'
HOW_2_BODY = 'একটি মডেল ছবিতে ইটভাটার প্রার্থী খুঁজে তার অবস্থান ও ধরন নথিভুক্ত করে।'
HOW_3_HEAD = 'নিয়ম যাচাই'
HOW_3_BODY = 'প্রতিটি প্রার্থীকে মানচিত্রে চিহ্নিত স্কুল, হাসপাতাল, বসতি, রেলপথ, বন ও জলাভূমির সাথে তুলনা করা হয়।'
HOW_4_HEAD = 'অগ্রাধিকার নির্ধারণ'
HOW_4_BODY = 'প্রার্থীদের উচ্চ, মাঝারি ও নিম্ন অগ্রাধিকারে ভাগ করা হয়, যা একে অপরের তুলনায়, চূড়ান্ত ঝুঁকি নয়।'
ABOUT_DATA_TITLE = 'তথ্য'
ABOUT_DATA_DATE = 'তথ্য যে তারিখ পর্যন্ত'
ABOUT_SOURCES = 'উৎস'
ABOUT_SOURCES_VALUE = 'সেন্টিনেল-২ স্যাটেলাইট ছবি; ওপেনস্ট্রিটম্যাপের মানচিত্র তথ্য'
ABOUT_COVERAGE = 'আওতা'
ABOUT_COVERAGE_FMT = '{0}টি জেলা, {1}টি ইটভাটার প্রার্থী'
ABOUT_TEAM = 'দল'
ABOUT_METHODOLOGY = 'পদ্ধতি ও সীমাবদ্ধতা পড়ুন'
ABOUT_METHODS_TITLE = 'পদ্ধতি ও সীমাবদ্ধতা'
ABOUT_METHODS_BODY = (
    'এখানে দেখানো ইটভাটার প্রার্থী Sentinel-2 ছবির তথ্য থেকে এসেছে। কাছের স্থানের তথ্য '
    'ধোঁয়ায় থাকা OpenStreetMap-এর চিহ্ন থেকে নেওয়া; মানচিত্রের তথ্যের কোনো স্থান অনুপস্থিত হলে '
    'তা এখানে নাও দেখা যেতে পারে। আওতা নির্ভর করে পাওয়া ছবি ও মানচিত্রের তথ্যের ওপর। '
    'জমা দেওয়া রিপোর্ট কর্মীদের ইনবক্সে যায়।'
)
ABOUT_PRIVACY_TITLE = 'গোপনীয়তা'
ABOUT_PRIVACY_BODY = (
    'সাধারণ ব্যবহারে ব্যবহারকারীর প্রোফাইল বা খোঁজার ইতিহাস সংরক্ষণ করা হয় না। '
    'রিপোর্ট জমা দিলে তার অবস্থান, কারণ, নোট, জমা দেওয়ার সময় এবং ঐচ্ছিক যোগাযোগের তথ্য বা ছবি '
    'কর্মীদের দেখার জন্য সংরক্ষণ করা হয়।'
)
STATE_RETRY = 'আবার চেষ্টা করুন'
STATE_ERROR_TITLE = 'কিছু একটা ভুল হয়েছে'
STATE_ERROR_BODY = 'পাতার এই অংশটি দেখানো যায়নি। আপনার ফিল্টার ঠিক আছে। অনুগ্রহ করে আবার চেষ্টা করুন।'
STATE_DATA_TITLE = 'তথ্য লোড করা যায়নি'
STATE_DATA_BODY = 'অনুগ্রহ করে সংযোগ পরীক্ষা করে একটু পরে আবার চেষ্টা করুন।'
STATE_LOADING = 'ভাটার তথ্য লোড হচ্ছে…'
LIST_ARIA_LABEL = 'ইটভাটার প্রার্থী'
LIST_ARIA_SELECT_FMT = '{0}: {1}'

# --- P10: voice guide ---
VOICE_READ_ALOUD = '🔊 পড়ে শোনান'
VOICE_STOP = '⏹ থামান'
VOICE_NO_VOICE = 'এই ব্রাউজারে এই ভাষার কণ্ঠস্বর নেই। অনুগ্রহ করে নির্দেশিকাটি পড়ুন।'
VOICE_TRANSCRIPT = 'লেখাটি পড়ুন'
VOICE_INSPECTOR_SCRIPT = 'পরিদর্শক ভিউতে আপনি মানচিত্রে সব ইটভাটার প্রার্থী দেখতে পারবেন। প্রথমে বামের ফিল্টার খুলুন। জেলা, এলাকা, ইটভাটার ধরন, অগ্রাধিকার অথবা নিয়মের সংকেত বাছুন, তারপর ফিল্টার প্রয়োগ করুন চাপুন। এরপর অগ্রাধিকারের তালিকা থেকে একটি ইটভাটা বাছুন, অথবা মানচিত্রের চিহ্নে চাপ দিন। নিচে সেটির তথ্য দেখা যাবে, যার মধ্যে কাছের স্কুল, হাসপাতাল ও অন্যান্য স্থান থেকে দূরত্বও আছে। মানচিত্রে রাস্তার মানচিত্র ও স্যাটেলাইট ছবির মধ্যে বদলাতে পারেন, আর ঘনত্বের হিটম্যাপ চালু করতে পারেন, যা দেখায় কোথায় অনেক ভাটা কাছাকাছি আছে। এটি ঝুঁকি দেখায় না। রেকর্ড রাখতে ফিল্টার করা তালিকা সিএসভি ফাইলে, অথবা নির্বাচিত ইটভাটার পিডিএফ প্রতিবেদন ডাউনলোড করুন। উচ্চ, মাঝারি ও নিম্ন অগ্রাধিকার সব প্রার্থীর মধ্যে আপেক্ষিক ভাগ। এটি চূড়ান্ত ঝুঁকির মাপ নয়।'
VOICE_COMMUNITY_SCRIPT = 'ধোঁয়ায় আপনাকে স্বাগত। এই পাতায় আপনার কাছাকাছি ইটভাটার প্রার্থী খুঁজে পাবেন। প্রথম ধাপ: জেলা, উপজেলা বা কাছের এলাকার নাম খুঁজতে কয়েকটি অক্ষর লিখুন, তারপর একটি পরামর্শ বেছে নিন। অথবা আমার অবস্থান ব্যবহার করুন চাপুন। দ্বিতীয় ধাপ: কত দূর পর্যন্ত খুঁজবেন, তা বেছে নিন। দূরত্ব কিলোমিটারে বাছুন। পুরো উপজেলা বা জেলা বাছলে সেই এলাকার সব ভাটা দেখানো হয়। তৃতীয় ধাপ: ফলাফল দেখুন। সংক্ষিপ্ত সারাংশ, তালিকা ও মানচিত্র পাবেন। মানচিত্রে কোনো চিহ্নে চাপ দিলে সেই ভাটার তথ্য দেখতে পাবেন। অন্যদের সাথে ভাগ করতে প্রতিবেদন বা তালিকা ডাউনলোড করতে পারেন। অগ্রাধিকারের রং একে অপরের তুলনায় ঠিক করা। এটি চূড়ান্ত ঝুঁকির মাপ নয়।'

# --- S1: four sections, Inspector Portal sign-in
NAV_INSPECTOR = '🔒 পরিদর্শক পোর্টাল'
PORTAL_SIGNIN_TITLE = 'পরিদর্শক পোর্টাল'
PORTAL_SIGNIN_HINT = 'এই অংশটি কর্মীদের জন্য। চালিয়ে যেতে আপনার নাম ও পাসওয়ার্ড দিন।'
PORTAL_PASSCODE = 'পাসওয়ার্ড'
PORTAL_NAME = 'আপনার নাম'
PORTAL_SIGN_IN = 'প্রবেশ করুন'
PORTAL_WRONG_PASSCODE = 'পাসওয়ার্ডটি সঠিক নয়। আবার চেষ্টা করুন।'
PORTAL_SIGNIN_UNAVAILABLE = 'কর্মীদের প্রবেশ এই মুহূর্তে চালু নেই।'
PORTAL_DEMO_CREDENTIALS_HINT = 'DoE Inspector'
PORTAL_FILL_DEMO_CREDENTIALS = 'DoE Inspector হিসেবে প্রবেশ করুন'
PORTAL_PASSWORD_REQUIREMENTS = 'কমপক্ষে ১২ অক্ষর; বড় ও ছোট হাতের অক্ষর, একটি সংখ্যা এবং একটি প্রতীক থাকতে হবে।'
PORTAL_FORGOT_PASSWORD = 'পাসওয়ার্ড ভুলে গেছেন?'
PORTAL_REGISTER = 'নিবন্ধন করুন'
PORTAL_ACCOUNT_ACTION_UNAVAILABLE = 'পাসওয়ার্ড পুনরুদ্ধার ও নতুন অ্যাকাউন্ট নিবন্ধন এখনো চালু হয়নি।'
PORTAL_DEMO_INSPECTOR = 'DoE Inspector'
PORTAL_DEMO_CREDENTIALS_FMT = 'ডেমো লগইন — নাম: {0} · পাসওয়ার্ড: {1}'
PORTAL_SIGNED_IN_FMT = 'প্রবেশ করেছেন: {0}'
PORTAL_SIGN_OUT = 'বের হয়ে যান'
PORTAL_TAB_DASHBOARD = 'ড্যাশবোর্ড'
PORTAL_TAB_MAP = 'মানচিত্র'
PORTAL_TAB_WORK = 'কাজ'
PORTAL_TAB_REPORTS = 'প্রতিবেদন'
PORTAL_TAB_REPORTS_FMT = 'প্রতিবেদন ({0})'
PORTAL_TABS_LABEL = 'পরিদর্শক পোর্টালের অংশ'
PORTAL_SOON_TITLE = 'শীঘ্রই আসছে'
PORTAL_SOON_BODY = 'এই অংশটি পরবর্তী হালনাগাদে পাওয়া যাবে।'
WORK_STATUS = 'পরিদর্শনের অবস্থা'
WORK_NOT_VISITED = 'পরিদর্শন হয়নি'
WORK_ASSIGNED = 'দায়িত্ব দেওয়া হয়েছে'
WORK_VISITED = 'পরিদর্শন হয়েছে'
WORK_CONFIRMED_ACTIVE = 'সক্রিয় ভাটা নিশ্চিত'
WORK_NOT_A_KILN = 'ভাটা নয়'
WORK_ASSIGN_TO_ME = 'আমাকে দায়িত্ব দিন'
WORK_SAVE_STATUS = 'অবস্থা সংরক্ষণ করুন'
WORK_ADD_NOTE = 'নোট যোগ করুন'
WORK_NOTE_HINT = 'নোট লিখুন'
WORK_HISTORY = 'পরিদর্শনের ইতিহাস'
WORK_CURRENT_ASSIGNEE = 'দায়িত্বে: {0}'
WORK_MY_LIST = 'আমার পরিদর্শনের তালিকা'
WORK_STATUS_FILTER = 'অবস্থা অনুযায়ী দেখুন'
WORK_SORT = 'সাজানোর ধরন'
WORK_SORT_PRIORITY = 'অগ্রাধিকার'
WORK_SORT_DISTANCE = 'দূরত্ব'
WORK_DISTANCE_ORIGIN = 'যেখান থেকে দূরত্ব'
WORK_EMPTY = 'এই বাছাইয়ে কোনো পরিদর্শন নেই।'
WORK_EMPTY_MAP_HINT = 'পরিদর্শনের তালিকায় যোগ করতে Inspector Map থেকে একটি ভাটা বেছে নিয়ে নিজের নামে দায়িত্ব নিন।'
WORK_OPEN_INSPECTOR_MAP = 'Inspector Map খুলুন'
WORK_ALL = 'সব পরিদর্শন'
WORK_OPEN_MAP = 'মানচিত্রে খুলুন'
WORK_DIRECTIONS = 'দিকনির্দেশনা'
WORK_ROUTES = 'আমার পরিদর্শনের রুট'
WORK_ROUTE_FMT = 'রুট {0} খুলুন ({1}–{2})'
WORK_ROUTE_NOTE = 'রুটটি তালিকার প্রথম ভাটা থেকে শুরু হয়ে তালিকার ক্রম অনুসরণ করে। রাস্তার পথ Google Maps দেখায়।'
WORK_VISIT_PHOTO = 'পরিদর্শনের ছবি'
WORK_ATTACH_PHOTO = 'ছবি সংযুক্ত করুন'
WORK_PHOTO_SAVED = 'পরিদর্শনের ছবি সংরক্ষিত হয়েছে।'
WORK_PHOTO_INVALID = 'JPEG, PNG বা WebP ছবি বেছে নিন।'
WORK_ACTIVITY = 'সাম্প্রতিক কাজ'
WORK_ACTIVITY_VISIT = 'পরিদর্শনের অবস্থা বা দায়িত্ব পরিবর্তন'
WORK_ACTIVITY_NOTE = 'পরিদর্শনের নোট যোগ'
WORK_ACTIVITY_PHOTO = 'পরিদর্শনের ছবি যোগ'
WORK_ACTIVITY_FILTER_SAVED = 'সংরক্ষিত বাছাই তৈরি বা হালনাগাদ'
WORK_ACTIVITY_FILTER_DELETED = 'সংরক্ষিত বাছাই মুছে ফেলা'
WORK_ACTIVITY_REPORT = 'প্রতিবেদনের অবস্থা পরিবর্তন'
WORK_ACTIVITY_STATUS_FMT = 'অবস্থা: {0}; দায়িত্বে: {1}'
SAVED_FILTERS = 'সংরক্ষিত বাছাই'
SAVED_FILTER_NAME = 'বাছাইয়ের নাম'
SAVED_FILTER_SAVE = 'বর্তমান বাছাই সংরক্ষণ করুন'
SAVED_FILTER_SELECT = 'সংরক্ষিত বাছাই বেছে নিন'
SAVED_FILTER_NONE = 'আপনার কোনো সংরক্ষিত বাছাই নেই।'
SAVED_FILTER_APPLY = 'মানচিত্রে বাছাই খুলুন'
SAVED_FILTER_DELETE = 'সংরক্ষিত বাছাই মুছুন'
SAVED_FILTER_SAVED = 'বাছাই সংরক্ষিত হয়েছে।'
SAVED_FILTER_NAME_REQUIRED = 'বাছাইয়ের একটি নাম লিখুন।'
SAVED_FILTER_CURRENT_FMT = 'বর্তমান বাছাই: {0} · {1} · {2} · {3}'
REPORT_INBOX = 'কমিউনিটি প্রতিবেদন'
REPORT_EMPTY = 'এখনো কোনো প্রতিবেদন নেই।'
REPORT_STATUS = 'প্রতিবেদনের অবস্থা'
REPORT_NEW = 'নতুন'
REPORT_REVIEWED = 'পর্যালোচিত'
REPORT_RESOLVED = 'সমাধান হয়েছে'
REPORT_MARK_REVIEWED = 'পর্যালোচিত হিসেবে চিহ্নিত করুন'
REPORT_MARK_RESOLVED = 'সমাধান হিসেবে চিহ্নিত করুন'
REPORT_OPEN_MAP = 'অবস্থান মানচিত্রে খুলুন'
PORTAL_OPEN_REPORTS_FMT = 'নতুন/পর্যালোচনাধীন প্রতিবেদন: {0}'

# S2: public Overview (no priority wording)
PUB_HERO_MISSION = 'স্যাটেলাইট ছবি থেকে শনাক্ত করা ইটভাটার প্রার্থী, মানচিত্রে দেখানো।'
PUB_HERO_SUB = 'আপনার বাড়ি বা গ্রামের কাছের ইটভাটার প্রার্থীগুলো খুঁজে নিন।'
PUB_OV_DISTRICTS_HINT = 'জেলার নামে চাপলে সেই জেলার ইটভাটার প্রার্থী দেখা যাবে।'
PUB_OV_OPEN_DISTRICT_FMT = '{0}-এর ইটভাটার প্রার্থী দেখুন'
PUB_HOW_3_HEAD = 'কাছের ভাটা খোঁজা'
PUB_HOW_3_BODY = 'প্রার্থীদের মানচিত্রে দেখানো হয়, যাতে কোনো এলাকার কাছের ভাটাগুলো খুঁজে নেওয়া যায়।'

# FAQ section (About page)
FAQ_TITLE = 'সাধারণ জিজ্ঞাসা'
FAQ_Q1 = 'ধোয়া কী?'
FAQ_A1 = 'ধোয়া বাংলাদেশের স্যাটেলাইট ছবি থেকে শনাক্ত করা ইটভাটার প্রার্থীদের একটি পাবলিক মানচিত্র। এটি স্থানীয় মানুষ ও গবেষকদের কাছাকাছি ভাটা খুঁজে পেতে ও প্রতিবেদন দিতে সাহায্য করে।'
FAQ_Q2 = 'আমার গ্রামের কাছের ভাটা কীভাবে খুঁজব?'
FAQ_A2 = "'কাছের ভাটা' পাতায় যান এবং অনুসন্ধান বাক্সে আপনার গ্রাম বা জেলার নাম লিখুন, অথবা 'আমার অবস্থান ব্যবহার করুন' বোতামে চাপ দিন।"
FAQ_Q3 = '"প্রার্থী" মানে কী?'
FAQ_A3 = 'প্রার্থী হলো এমন একটি স্থান যেখানে স্যাটেলাইট মডেল ইটভাটা থাকার সম্ভাবনা চিহ্নিত করেছে।'
FAQ_Q4 = 'কোনো ভাটা কীভাবে রিপোর্ট করব?'
FAQ_A4 = "'কাছের ভাটা' পাতায় তালিকা থেকে ভাটাটি খুঁজে 'এই ভাটিটি রিপোর্ট করুন' বোতামে চাপ দিন। আপনার পর্যবেক্ষণ লিখে জমা দিন — এটি আমাদের পর্যালোচনা দলের কাছে যাবে।"
FAQ_Q5 = 'ভাটা রিপোর্ট করার পর কী হয়?'
FAQ_A5 = 'আপনার রিপোর্ট পরিদর্শক পোর্টালে পর্যালোচনার জন্য যায়। পরিদর্শক মানচিত্রে অবস্থান দেখতে, প্রতিবেদন ডাউনলোড করতে এবং পর্যালোচিত বা সমাধান হয়েছে হিসেবে চিহ্নিত করতে পারেন।'
FAQ_Q6 = 'ভাষা কীভাবে বদলাব?'
FAQ_A6 = 'পাতার উপরে EN / বাং টগল ব্যবহার করে ইংরেজি ও বাংলার মধ্যে যাওয়া-আসা করা যাবে।'

# Chatbot
CHAT_PLACEHOLDER = 'প্রশ্ন করুন বা এলাকা, জেলা, উপজেলা কিংবা স্থানের নাম লিখুন…'
CHAT_TITLE = '💬 সাহায্য'
CHAT_WELCOME = 'হ্যালো! কাছের ভাটা খুঁজতে জেলা, উপজেলা বা কোনো পরিচিত স্থানের নাম লিখুন। ধোঁয়া ব্যবহার নিয়েও প্রশ্ন করতে পারেন।'
CHAT_FALLBACK = 'ধোঁয়া, প্রতিবেদন বা কাছের ভাটার প্রার্থী খুঁজতে আমি সাহায্য করতে পারি। “প্রার্থী বলতে কী বোঝায়?” জিজ্ঞাসা করুন, অথবা কোনো স্থানের নাম লিখে খুঁজুন।'
CHAT_FOLLOW_UP = 'আর কী জানতে চান?'
CHAT_GO_DISTRICT = '{0}-এর ভাটা দেখাচ্ছি। মানচিত্র খুলছে…'
CHAT_AREA_AMBIGUOUS = 'একাধিক এলাকার সাথে মিলেছে। সঠিকটি খুঁজতে স্থানের সাথে জেলা বা উপজেলার নাম লিখুন: {0}।'
CHAT_SEARCH_PLACE_FMT = "আপনার এলাকার কাছাকাছি ভাটার মানচিত্র প্রস্তুত!"
CHAT_GO_NEAR_ME = "'কাছের ভাটা' খুলছে…"
CHAT_GO_OVERVIEW = 'ওভারভিউ মানচিত্র খুলছে…'
CHAT_GO_ABOUT = 'পরিচিতি পাতা খুলছে…'
CHAT_GO_INSPECTOR = 'পরিদর্শক পোর্টাল খুলছে…'
CHAT_HOW_REPORT = "'কাছের ভাটা' পাতায় ভাটাটি খুঁজুন, তারপর সেই সারিতে 'এই ভাটিটি রিপোর্ট করুন' বোতামে চাপ দিন।"
CHAT_WHAT_CANDIDATE = 'প্রার্থী হলো স্যাটেলাইট মডেলের চিহ্নিত সম্ভাব্য ইটভাটা।'
CHAT_HOW_LANGUAGE = 'পাতার উপরে EN / বাং টগল ব্যবহার করে ভাষা পরিবর্তন করুন।'

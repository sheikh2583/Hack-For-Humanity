"""Fallback texts for the voice guide (used only when strings_bn/strings_en lack these names).

Same wording the pre-rendered mp3 files were made from, so the audio hash still matches.
"""

from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    "bn": {
        "LISTEN_TO_THE_GUIDE": '🔊 ব্যবহার নির্দেশিকা শুনুন',
        "VOICE_READ_ALOUD": '🔊 পড়ে শোনান',
        "VOICE_STOP": '⏹ থামান',
        "VOICE_NO_VOICE": 'এই ব্রাউজারে এই ভাষার কণ্ঠস্বর নেই। অনুগ্রহ করে নির্দেশিকাটি পড়ুন।',
        "VOICE_TRANSCRIPT": 'লেখাটি পড়ুন',
        "VOICE_INSPECTOR_SCRIPT": 'মানচিত্র পাতায় আপনি সব ইটভাটার প্রার্থী দেখতে পারবেন। কাছাকাছি খুঁজতে জায়গা বেছে নিন বা আমার অবস্থান ব্যবহার করুন চাপুন, তারপর কত কিলোমিটার দূর পর্যন্ত দেখবেন বাছুন। সব ইটভাটা দেখতে প্রথমে বামের ফিল্টার খুলুন। জেলা, এলাকা, ইটভাটার ধরন, অগ্রাধিকার অথবা নিয়মের সংকেত বাছুন, তারপর ফিল্টার প্রয়োগ করুন চাপুন। এরপর অগ্রাধিকারের তালিকা থেকে একটি ইটভাটা বাছুন, অথবা মানচিত্রের চিহ্নে চাপ দিন। নিচে সেটির তথ্য দেখা যাবে, যার মধ্যে কাছের স্কুল, হাসপাতাল ও অন্যান্য স্থান থেকে দূরত্বও আছে। মানচিত্রে রাস্তার মানচিত্র ও স্যাটেলাইট ছবির মধ্যে বদলাতে পারেন, আর ঘনত্বের হিটম্যাপ চালু করতে পারেন, যা দেখায় কোথায় অনেক ভাটা কাছাকাছি আছে। এটি ঝুঁকি দেখায় না। রেকর্ড রাখতে ফিল্টার করা তালিকা সিএসভি ফাইলে, অথবা নির্বাচিত ইটভাটার পিডিএফ প্রতিবেদন ডাউনলোড করুন। উচ্চ, মাঝারি ও নিম্ন অগ্রাধিকার সব প্রার্থীর মধ্যে আপেক্ষিক ভাগ। এটি চূড়ান্ত ঝুঁকির মাপ নয়।',
        "VOICE_COMMUNITY_SCRIPT": 'ধোঁয়ায় আপনাকে স্বাগত। এই পাতায় আপনার কাছাকাছি ইটভাটার প্রার্থী খুঁজে পাবেন। প্রথম ধাপ: কোথায় খুঁজবেন, তা বেছে নিন। তালিকা থেকে জেলা, উপজেলা বা এলাকার নাম বাছুন, অথবা আমার অবস্থান ব্যবহার করুন চাপুন। কীভাবে শুরু করবেন বুঝতে না পারলে, একটি উদাহরণ দেখুন চাপুন। দ্বিতীয় ধাপ: কত দূর পর্যন্ত খুঁজবেন, তা বেছে নিন। দূরত্ব কিলোমিটারে বাছুন। পুরো উপজেলা বা জেলা বাছলে সেই এলাকার সব ভাটা দেখানো হয়। তৃতীয় ধাপ: ফলাফল দেখুন। সংক্ষিপ্ত সারাংশ, তালিকা ও মানচিত্র পাবেন। মানচিত্রে কোনো চিহ্নে চাপ দিলে সেই ভাটার তথ্য দেখতে পাবেন। অন্যদের সাথে ভাগ করতে প্রতিবেদন বা তালিকা ডাউনলোড করতে পারেন। অগ্রাধিকারের রং একে অপরের তুলনায় ঠিক করা। এটি চূড়ান্ত ঝুঁকির মাপ নয়।',
    },
    "en": {
        "LISTEN_TO_THE_GUIDE": '🔊 Listen to the guide',
        "VOICE_READ_ALOUD": '🔊 Read aloud',
        "VOICE_STOP": '⏹ Stop',
        "VOICE_NO_VOICE": 'This browser has no voice for this language. Please read the guide instead.',
        "VOICE_TRANSCRIPT": 'Read the text',
        "VOICE_INSPECTOR_SCRIPT": 'Welcome to the Map page. Here you can explore every kiln candidate on the map. To look near you, choose a place or press Use my location, then pick a distance in kilometres. To browse every kiln instead, first open the filters on the left. Choose a district, area, kiln type, priority or rule signal, then press Apply filters. Next, pick a kiln from the priority list, or tap a marker on the map. Its details appear below, including distances to nearby schools, hospitals and other places. You can switch between the street map and satellite imagery, and turn on the density heatmap, which shows where many kilns sit close together. It does not show risk. To keep a record, download the filtered list as a CSV file, or a PDF report for the selected kiln. High, medium and low priority are relative groups across all candidates. They are not an absolute measure of risk.',
        "VOICE_COMMUNITY_SCRIPT": 'Welcome to Dhoa. This page helps you find brick kiln candidates near you. Step one: choose where to look. Pick a district, upazila or place from the list, or press Use my location. If you are not sure how to begin, press Try an example. Step two: choose how far. Pick a distance in kilometres. If you choose a whole upazila or district, every kiln in that area is shown. Step three: see the results. You get a short summary, a list and a map. Tap a marker on the map to see details for that kiln. You can download a report or the list to share. Priority colours are relative to each other. They are not an absolute measure of risk.',
    },
}

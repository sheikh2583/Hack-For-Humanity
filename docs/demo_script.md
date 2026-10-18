# ৩ মিনিটের লাইভ ডেমো স্ক্রিপ্ট

**সময়:** প্রায় ৩ মিনিট। **শুরু:** Dhoa অ্যাপ ইতিমধ্যে ব্রাউজারে খোলা এবং লোড সম্পন্ন। কোনো ফিল্টার বা অনুসন্ধান আগে থেকে সেট করা লাগবে না। প্রতিটি ধাপে বলা বাক্যটি ইংরেজিতে পড়ুন।

## Inspector walkthrough — প্রায় ১ মিনিট ৩০ সেকেন্ড

### Step 1 — Landing page (0:00–0:15)
- **ক্লিক/কাজ:** কিছু ক্লিক করবেন না। Inspector landing page-এ KPI, তালিকা ও মানচিত্র দেখা যাচ্ছে কি না নিশ্চিত করুন।
- **বলুন:** “This is Dhoa, a dashboard for exploring brick-kiln detection candidates across Bangladesh.”
- **দর্শক দেখবেন:** Dhoa শিরোনাম, Inspector view, KPI সারি, প্রার্থী তালিকা এবং মানচিত্র।

### Step 2 — জেলা ফিল্টার (0:15–0:35)
- **ক্লিক/কাজ:** বাম sidebar-এর `জেলা` dropdown খুলুন। এমন একটি জেলা বাছুন যার জন্য প্রার্থী ফল আসে।
- **বলুন:** “I’ll narrow the results to one district; the candidate list and map update to the same filtered set.”
- **দর্শক দেখবেন:** নির্বাচিত জেলা, বদলে যাওয়া তালিকা/সংখ্যা এবং সংশ্লিষ্ট মার্কার।

### Step 3 — উপজেলা ও ব্যাসার্ধ (0:35–0:55)
- **ক্লিক/কাজ:** `এলাকা (উপজেলা)` dropdown খুলে ওই জেলার একটি ফলযুক্ত উপজেলা বাছুন। `অনুসন্ধান ব্যাসার্ধ` স্লাইডার ১,০০০ মিটারে টানুন।
- **বলুন:** “Now I’m focusing on one upazila and applying a radius around the average location of its kiln candidates.”
- **দর্শক দেখবেন:** নির্বাচিত উপজেলা ও ব্যাসার্ধ অনুযায়ী সংকুচিত প্রার্থী তালিকা এবং মানচিত্র।

### Step 4 — শুধু উচ্চ অগ্রাধিকার (0:55–1:15)
- **ক্লিক/কাজ:** `অগ্রাধিকার` multiselect খুলুন, `মাঝারি` ও `নিম্ন` অপশন সরান, শুধু `উচ্চ` রাখুন।
- **বলুন:** “The priority filter lets an inspector focus on the high-priority candidates first.”
- **দর্শক দেখবেন:** শুধু উচ্চ অগ্রাধিকারের সারি ও মার্কার।

### Step 5 — ভাটার পপআপ (1:15–1:30)
- **ক্লিক/কাজ:** তালিকার ফলযুক্ত ভাটার মার্কারে একবার ক্লিক করুন। পপআপ খুললে সেটি দৃশ্যমান রাখুন।
- **বলুন:** “Clicking a marker opens the candidate’s location, kiln type, confidence, priority, and mapped signals.”
- **দর্শক দেখবেন:** খোলা marker popup এবং নির্বাচিত প্রার্থীর বিস্তারিত।

## Community walkthrough — প্রায় ১ মিনিট ৩০ সেকেন্ড

### Step 6 — Community view-তে যান (1:30–1:40)
- **ক্লিক/কাজ:** পৃষ্ঠার view selector-এ `কমিউনিটি ভিউ` ক্লিক করুন.
- **বলুন:** “The Community view starts with a place-name search instead of coordinates.”
- **দর্শক দেখবেন:** Community view-এর স্থান অনুসন্ধান ফর্ম।

### Step 7 — কাছাকাছি ভাটা খুঁজুন (1:40–2:05)
- **ক্লিক/কাজ:** `নাম লিখুন` ঘরে `Ashulia` লিখুন এবং `🔎 অনুসন্ধান করুন` বোতাম ক্লিক করুন। ফল না এলে অন্য একটি পরিচিত বাংলাদেশি স্থানের নাম লিখে আবার অনুসন্ধান করুন। অন্তত একটি ফল না আসা পর্যন্ত Community `অনুসন্ধানের ব্যাসার্ধ` স্লাইডার বাড়ান।
- **বলুন:** “Dhoa geocodes the place name, then shows candidates within the selected search radius.”
- **দর্শক দেখবেন:** ফলের সংখ্যা, দূরত্ব ও এলাকা-সহ তালিকা, directions link এবং অনুসন্ধান বৃত্তসহ মানচিত্র।

### Step 8 — রিপোর্ট টেক্সট প্রস্তুত (2:05–2:40)
- **ক্লিক/কাজ:** ফলের নিচে `ভাটা রিপোর্ট করুন` শিরোনাম খুঁজুন। `⚠️ এই ভাটাটি রিপোর্ট করুন` expander খুলুন। ভাটা নির্বাচনের dropdown থেকে একটি ফল বাছুন। `📋 রিপোর্ট টেক্সট কপি করুন` ক্লিক করুন।
- **বলুন:** “Selecting a kiln fills a report template with its area, nearest place, approximate location, priority, and signal count. The code block can be copied manually.”
- **দর্শক দেখবেন:** pre-filled read-only report text এবং বোতাম ক্লিকের পরে copyable code block।

### Step 9 — হেল্পলাইন তথ্য (2:40–3:00)
- **ক্লিক/কাজ:** রিপোর্ট expander-এর নিচের info box দেখান; প্রয়োজনে সামান্য নিচে scroll করুন।
- **বলুন:** “The page also displays the 333, then 4 helpline information. Please confirm current official instructions before acting on them.”
- **দর্শক দেখবেন:** `সরকারি পরিবেশ হেল্পলাইন: 333 → 4 চাপুন` info box।

## ডেমো শেষে

- **ক্লিক/কাজ:** আর কোনো submit বা report send করবেন না; এটি কেবল কপি করার ডেমো।
- **বলুন:** “That concludes the walkthrough: location-based inspection, community search, and a user-controlled report text flow.”
- **দর্শক দেখবেন:** Community ফল ও হেল্পলাইন তথ্য।

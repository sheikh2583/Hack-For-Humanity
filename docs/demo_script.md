# Dhoa public report-to-staff demo

Two timed versions below show the same public-to-staff flow. Each takes about
60 seconds. Use the current app labels and switch language before the relevant
run. Select a place and candidate that appear in the loaded dataset; the
example place name below is present in the current processed data.

## Before the demo

Run the dashboard with a temporary report database, separate from any shared
or deployed database. In PowerShell:

```powershell
$env:DHOA_APP_DB = "$env:TEMP\dhoa-demo\app.db"
$env:DHOA_DEMO_MODE = "1"
$env:DHOA_STAFF_PASSCODE = "dhoa-demo-only"
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

Create the temporary directory first if it does not exist. Demo mode adds a
button that fills the configured dummy passcode and Demo name; it does not
sign in automatically or create demo reports. Submit only the
explicitly labelled demo report below. Delete the temporary demo directory
after the presentation. Do not submit demo records to the shared or deployed
app.

## English run — about 60 seconds

| Time | Action | Say |
|---|---|---|
| 0:00–0:12 | Open the public search. Search for `Block C` using the place picker, then show the results. | “I can search for a place and explore the kiln candidates shown nearby.” |
| 0:12–0:25 | Open the report action on one result. Choose a reason and enter `DEMO ONLY — example report for the presentation` as the note. Submit. | “A community member can send a report to the staff inbox. This sample is clearly marked and stored only in the temporary demo database.” |
| 0:25–0:38 | Open Inspector Portal, click **Fill demo credentials**, then click **Sign in**. Open Reports and point out the new-report count and submitted item. | “Staff can see the new report and open its location on the map.” |
| 0:38–0:55 | Open the report location on the map. In the candidate's work controls, choose **Assign to me**, set status to **Visited**, save, then add the note `DEMO ONLY — presentation record`. | “Staff can assign the candidate, record a visit, and add a note.” |
| 0:55–1:00 | Sign out of the portal. | “That completes the public report-to-staff workflow.” |

If `Block C` is no longer offered by the loaded dataset, choose a place from
the live picker instead. Do not type a guessed location or coordinates.

## বাংলা রান — প্রায় ৬০ সেকেন্ড

| সময় | কাজ | বলুন |
|---|---|---|
| ০:০০–০:১২ | সাধারণ ব্যবহারকারীর খোঁজার পাতায় যান। স্থানের তালিকায় `Block C` খুঁজে ফলাফল দেখান। | “এখানে কোনো স্থানের নাম দিয়ে খুঁজে কাছের ইটভাটার প্রার্থীগুলো দেখা যায়।” |
| ০:১২–০:২৫ | একটি ফলের রিপোর্ট অপশন খুলুন। কারণ বেছে নোটে লিখুন `DEMO ONLY — presentation-এর নমুনা রিপোর্ট`। জমা দিন। | “সাধারণ ব্যবহারকারী কর্মীদের ইনবক্সে রিপোর্ট পাঠাতে পারেন। এটি শুধু ডেমোর নমুনা, অস্থায়ী ডেটাবেসেই থাকবে।” |
| ০:২৫–০:৩৮ | পরিদর্শক পোর্টাল খুলে **ডেমো হিসেবে চালিয়ে যান** বাছুন। প্রতিবেদন অংশে নতুন রিপোর্টের সংখ্যা ও জমা দেওয়া রিপোর্ট দেখান। | “কর্মীরা নতুন রিপোর্ট দেখতে এবং তার অবস্থান মানচিত্রে খুলতে পারেন।” |
| ০:৩৮–০:৫৫ | রিপোর্টের অবস্থান মানচিত্রে খুলুন। প্রার্থীর কাজের নিয়ন্ত্রণে **আমাকে দায়িত্ব দিন** চাপুন, অবস্থা **পরিদর্শন হয়েছে** করে সংরক্ষণ করুন, তারপর `DEMO ONLY — presentation record` নোট যোগ করুন। | “কর্মীরা দায়িত্ব নিতে, পরিদর্শনের অবস্থা লিখতে এবং নোট যোগ করতে পারেন।” |
| ০:৫৫–১:০০ | পোর্টাল থেকে সাইন আউট করুন। | “এতেই সাধারণ ব্যবহারকারীর রিপোর্ট থেকে কর্মীদের কাজের ধাপটি শেষ।” |

`Block C` তালিকায় না থাকলে অ্যাপে দেখানো অন্য কোনো স্থান বেছে নিন। অনুমান করে
কোনো স্থান বা স্থানাঙ্ক লিখবেন না।

## Demo record handling

The report and visit note are intentionally labelled `DEMO ONLY`. They are
created in the temporary database path configured above. Do not use personal
contact information or upload a real person's photo. The temporary records
are presentation fixtures, not real community reports.

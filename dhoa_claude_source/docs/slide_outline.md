# Hack for Humanity Bangladesh 2026 — স্লাইড আউটলাইন

> **তথ্য যাচাই:** SentinelKilnDB, 2,150 detections এবং 74.7% field-validated precision এখানে টিমের দেওয়া brief অনুযায়ী রাখা হয়েছে। স্লাইডে ব্যবহারের আগে প্রকল্পের নির্ভরযোগ্য ডেটা/মূল্যায়ন নথির সঙ্গে সংখ্যা ও সংজ্ঞা মিলিয়ে নিন।

## Slide 1 — বাংলাদেশের ইটভাটা পর্যবেক্ষণে ধোঁয়া
- Introduce Dhoa as a Bangladesh brick-kiln monitoring dashboard.
- State the presentation goal: find, prioritize, and inspect candidate kiln locations.
- Introduce the Hack for Humanity Bangladesh 2026 team.
- **Screenshot:** Shot 1 — Inspector landing page.
- **Speaker note:** “We’ll show how Dhoa turns satellite observations into a map that people can explore.”

## Slide 2 — বাংলাদেশে ইটভাটার দূষণ সমস্যা
- Explain why kiln emissions and their distribution matter to communities and public agencies.
- Describe the challenge of locating and tracking many dispersed kiln sites.
- Frame satellite-based screening as a way to guide attention and investigation.
- **Screenshot:** Shot 1 — Inspector landing page, as the Bangladesh-wide context visual.
- **Speaker note:** “The first challenge is knowing where to look and which locations deserve attention first.”

## Slide 3 — ডেটা: SentinelKilnDB
- Present SentinelKilnDB as the project’s kiln detection dataset.
- Report 2,150 detections, using the project’s verified count and definition.
- Report 74.7% field-validated precision, with the validation method and sample clearly cited.
- **Screenshot:** No app screenshot; use a dataset/validation graphic and cite the project source.
- **Speaker note:** “These figures describe the dataset and validation result; we’ll show the dashboard that uses the detections next.”

## Slide 4 — যেভাবে কাজ করে: শনাক্তকরণ থেকে অগ্রাধিকার
- Explain the YOLOv8s-OBB detection stage at a high level.
- Show how candidate attributes and mapped signals feed a priority score or priority band.
- Describe the output as an ordered set of locations for users to inspect in the dashboard.
- **Screenshot:** Shot 4 — selected kiln with its map popup open.
- **Speaker note:** “The model finds candidate kilns, then the dashboard helps users review them in context.”

## Slide 5 — Inspector: জেলা ধরে অনুসন্ধান
- Demonstrate selecting a district in the Inspector sidebar.
- Show the filtered candidate count, list, and map markers together.
- Explain that the same active filter state drives the visible results.
- **Screenshot:** Shot 2 — Inspector with district filter active.
- **Speaker note:** “An inspector can start broad and focus on one district without losing the map context.”

## Slide 6 — Inspector: উপজেলা, ব্যাসার্ধ ও অগ্রাধিকার
- Demonstrate selecting an upazila and setting the radius slider.
- Show the resulting candidate list and map, then isolate the `উচ্চ` priority band.
- Explain how local filtering helps users move from a broad view to a focused review.
- **Screenshot:** Shot 3 for upazila/radius; Shot 5 for high-only priority.
- **Speaker note:** “The filters narrow the same set of candidates by location, distance, and priority.”

## Slide 7 — কমিউনিটি ভিউ: কাছাকাছি ফল
- Demonstrate searching for a place and adjusting the Community radius if needed.
- Show nearby candidates, distances, area names, and directions links.
- Explain how the map and table support local exploration.
- **Screenshot:** Shot 6 — Community search results.
- **Speaker note:** “Community users can search by a place name and see nearby candidates in one view.”

## Slide 8 — রিপোর্টের তথ্য ও 333 হেল্পলাইন
- Show the report text populated from a selected kiln’s details.
- Demonstrate the copy-text button and the displayed code block for manual copying.
- Point out the in-app 333 → 4 helpline information; verify the service details before presenting them as official guidance.
- **Screenshot:** Shot 7 — report section with text; Shot 8 — helpline info box.
- **Speaker note:** “The dashboard prepares a text summary for the user to copy into their chosen reporting channel.”

## Slide 9 — সম্ভাব্য প্রভাব ও পরবর্তী পদক্ষেপ
- Discuss how a shared map and ranked candidate list could support more focused review.
- Identify next steps such as broader validation, user feedback, and operational partnerships.
- Separate measured project results from future impact targets.
- **Screenshot:** Shot 2 or Shot 6 — choose the view that best supports the team’s impact claim.
- **Speaker note:** “Our next step is to validate the workflow with users and measure whether it improves follow-up.”

## Slide 10 — দল
- Introduce each teammate and their role in the project.
- Credit data, modeling, dashboard, and presentation contributions as appropriate.
- Close with a contact or project link the team has approved for sharing.
- **Screenshot:** No app screenshot; use a team slide with approved names and roles.
- **Speaker note:** “Thank you; we’re happy to discuss the implementation, validation, and next steps.”

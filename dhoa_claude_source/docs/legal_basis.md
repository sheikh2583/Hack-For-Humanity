# Legal Basis and Verification Record

**Status:** Draft. No legal threshold in this project is verified. AI-assisted
desk research from Manus was reviewed against the official consolidated Act
and official 2020 Gazette scan on 2026-10-07. This improves the source trail;
it is not a legal opinion or a current-force determination.

This document is an evidence register, not legal advice. The values in
`config/rules.yaml` must remain `verified: false` until a person checks the
original Act and gazette text and records the evidence below.

## Sources To Verify

The following primary-source pages were opened during review of Manus's
research on 2026-10-07. The consolidated Act supports the section references
and numeric distances recorded below. This review did not exhaustively search
later Gazettes, repeal notices, or court decisions, and does not establish that
every provision remains in force or how statutory boundaries should be
represented in GIS.

- Brick Manufacturing and Kiln Establishment (Control) Act 2013 (Act 59 of 2013)
  as amended by Act 1 of 2019. Official consolidated Bangla text, amendments
  shown in brackets, opened during review:
  `https://bdlaws.minlaw.gov.bd/act-details-1140.html`. The 2019 amending
  gazette (Bangladesh Gazette Extra, 28 Feb 2019) amends section 8 on printed
  pp. 7259-7260. No official English translation was found, so every passage
  below is Bangla and the English readings are unverified translations.
- Bangladesh Gazette Extra, 9 Jan 2020, S.R.O. No. 07-Ain/2020, dated
  06-01-2020 (also shown as 16-01-2020 on the Department of Environment notice
  page). Listed as item 7 in the Legislative Division 2020 SRO index
  (`https://legislativediv.gov.bd/pages/static-pages/694032c235ce18e1c0561dfc`).
  Official Gazette scan:
  `https://www.dpp.gov.bd/upload_file/gazettes/34909_20337.pdf`. Its header
  and date were confirmed, but the scan's full text was not independently
  transcribed in this review. Manus's reading of the narrow 400 m exception
  remains a secondary transcription pending reliable text verification. No
  repeal notice was found in the research reviewed; that is not a finding that
  it remains operative.
- Any official public kiln or licence register used for validation. Record its
  owner, release date, coverage, field definitions, and licence here. The dossier
  found none: the only named government list is a scanned Department of
  Environment closure list for January 2024 (98 rows nationwide, 5 in Gazipur,
  none in Chapainawabganj), which is not a licence register or a complete
  inventory.

## Rule Evidence Table

Complete one row for every rule and technology flag in `config/rules.yaml`.

| Config item | Exact source passage | Unit and interpretation | Reviewer/date | Verified? |
|---|---|---|---|---|
| `technology` (flag FCBK) | No passage found. Section 2 defines a kiln by performance (improved technology, fuel-efficient, air pollution within the Environment Conservation Rules 1997 limits); section 4A bars operating any kiln other than that defined kiln. No named permitted or banned technology appears in the Act, the 2019 amendment or Form-A. | The FCBK flag and the "Zigzag permitted" idea are project heuristics, not statutory text. The 2020 SRO names Hybrid Hoffman and Tunnel kilns only inside its 400 m exception. | Pending | No |
| `near_school`, `near_hospital` (1000 m) | s.8(3)(ঙ): at least 1 km from listed special installations, railways, educational institutions, hospitals and clinics, research institutions or similar. | The number 1 km is present in the official consolidated text. The precise legal reference geometry is unresolved; code measures from the kiln centroid to OSM features. | Pending | No |
| `near_settlement` (1000 m) | s.8(1)(ক)(খ) prohibits kilns in residential, reserved or commercial areas and at city corporation, municipality or upazila headquarters; s.8(3)(ক) sets 1 km from those prohibited-area boundaries. s.8 explanation: a residential area has at least 50 families. | The number 1 km and 50-family definition appear in the official consolidated text. OSM settlement polygons do not establish those legal categories or family counts; GIS proxy unresolved. | Pending | No |
| `near_forest` (2000 m; removed from active rules) | s.8(3)(খ): 2 km from the boundary of **government** forest. Private forest, sanctuaries, gardens and wetlands are in s.8(1)(গ), so the general 1 km prohibited-area distance may apply. s.8 explanation defines private forest using Forest Department recognition and at least 30% crown cover. | The Act distinguishes government forest from generic forest. This rule was removed from active screening because the available OSM layer is generic and no authoritative pilot-area government-forest layer has been confirmed. | Pending | No |
| `near_wetland` (1000 m; removed from active rules) | s.8(1)(গ) lists wetlands; s.8 explanation defines a wetland as land submerged at least six months a year; s.8(3)(ক) gives 1 km from prohibited-area boundaries. | The statutory definition and distance appear in the consolidated text. Generic OSM `water` is not a legal wetland layer; this rule was removed from active screening. | Pending | No |
| 2020 SRO 400 m (no config entry) | Manus transcribes S.R.O. 07-Ain/2020 as a narrow exception for certain existing advanced-technology kilns, including Hybrid Hoffman and Tunnel, subject to air-quality and workplace conditions, with new kilns excluded. | Gazette header/date and official source confirmed; full text not independently transcribed here. Do not implement the exception or apply 400 m to detections until the Bangla text, scope, and current force are checked. | Pending | No |
| Section 8 proviso (2019) | Government may relax other conditions for kilns that existed before commencement if area air standards are met; it excludes s.8(1)(ঙ) and s.8(3)(খ)-(ঘ). | Matches `legal_status_caveat` and `forest_hill_note` in `config/rules.yaml`. Imagery cannot show establishment date, so flags stay candidates. | Pending | No |
| Not implemented: agricultural land, ecologically critical areas, hills, railways, degraded air sheds | s.8(1)(ঘ) agricultural land, (ঙ) ecologically critical areas, (চ) degraded air shed; s.8(3)(গ) 0.5 km from hills; s.8(3)(ঙ) railways; s.5(1) bars taking soil from agricultural land or hills for bricks. | Listed in `not_implemented` in `config/rules.yaml`. No public polygon layer was confirmed for ecologically critical areas; Protected Planet, HDX and the BFIS layer each carry caveats recorded in the dossier. | Pending | No |
| Road distance (none) | No road-distance rule in the Act, the 2019 gazette or the official pages reviewed. | Do not add a road rule without a primary source. The Act names railways, not ordinary roads. | Pending | No |

The legal distances and definitions above appear in the official consolidated
Act, but the project's GIS implementations and the law's current force are not
thereby verified. Do not change a `verified` flag or numeric threshold based on
a secondary summary, search result, model output, or this template. The
application must continue to label outputs as advisory while any rule remains
unverified.

## Open Questions

- Severity values (1-3) are project choices, not legal text. Manus's report supports
  distances only.
- What authoritative spatial boundaries and reference points implement each
  statutory distance in the pilot area?
- Does a later Gazette, amendment, repeal, or court order alter the provisions
  reviewed here?
- Which kiln technologies can the detector distinguish, and which require
  field or registry verification?
- What official source, if any, defines ecological-critical-area or public
  forest boundaries for the pilot districts?

## Human Sign-Off

Before changing any rule to verified, attach or cite the primary source,
record the exact passage and units in the table, have an independent reviewer
check it, and rerun the rules tests and a synthetic end-to-end example.

**Not verified by this project:** legal interpretation, threshold correctness,
licence-register completeness, and enforcement suitability.

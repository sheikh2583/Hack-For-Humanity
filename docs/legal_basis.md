# Legal Basis and Verification Record

**Status:** Draft. No legal threshold in this project is verified.

This document is an evidence register, not legal advice. The values in
`config/rules.yaml` must remain `verified: false` until a person checks the
original Act and gazette text and records the evidence below.

## Sources To Verify

Candidate locations below come from the research evidence dossier (accessed
2026-09-29 by its authors). **They have not been opened or checked by the
maintainers of this repository**; a person must open each and confirm the passage.

- Brick Manufacturing and Kiln Establishment (Control) Act 2013 (Act 59 of 2013)
  as amended by Act 1 of 2019. Consolidated Bangla text (the dossier's best
  current operative text, amendments shown in brackets):
  `http://bdlaws.minlaw.gov.bd/act-details-1140.html`. The 2019 amending
  gazette (Bangladesh Gazette Extra, 28 Feb 2019) amends section 8 on printed
  pp. 7259-7260. No official English translation was found, so every passage
  below is Bangla and the English readings are unverified translations.
- Bangladesh Gazette Extra, 9 Jan 2020, S.R.O. No. 07-Ain/2020, dated
  06-01-2020 (also shown as 16-01-2020 on the Department of Environment notice
  page). Listed as item 7 in the Legislative Division 2020 SRO index
  (`http://legislativediv.gov.bd/pages/static-pages/694032c235ce18e1c0561dfc`),
  which was still listing it when updated 04-06-2026. No repeal notice was
  found; that is not a finding that it remains operative. The gazette is a
  one-page image scan, so its text is a transcription.
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
| `near_school`, `near_hospital` (1000 m) | s.8(3)(ঙ), Bangladesh Laws line 62: at least 1 km from special installations, railways, educational institutions, hospitals and clinics, research institutions or similar. | 1 km, distance from the boundary of the place. Candidate match for 1000 m. The code measures from the kiln centroid and the OSM feature, not from legal boundaries. | Pending | No |
| `near_settlement` (1000 m) | s.8(1)(ক)(খ) prohibits kilns in residential, reserved or commercial areas and at city corporation, municipality or upazila headquarters; s.8(3)(ক) sets 1 km from the boundary of those areas. s.8 explanation: a residential area has at least 50 families. | 1 km. OSM settlement polygons do not tell whether 50 families live there, so this is an over-inclusive proxy. | Pending | No |
| `near_forest` (2000 m) | s.8(3)(খ): 2 km from the boundary of **government** forest. Private forest, sanctuaries, gardens and wetlands are in s.8(1)(গ), so 1 km via s.8(3)(ক). s.8 explanation: private forest needs Forest Department recognition and at least 30% crown cover. | A single 2000 m buffer on every OSM "forest" over-applies to non-government forest. Needs a government-forest layer; the dossier found no current official polygon download. | Pending | No |
| `near_wetland` (1000 m) | s.8(1)(গ) lists wetlands; s.8 explanation: land submerged at least six months a year; s.8(3)(ক) gives 1 km. | 1 km. OSM "water" includes rivers, ponds and seasonal water, so it is not the legal definition. | Pending | No |
| 2020 SRO 400 m (no config entry) | S.R.O. 07-Ain/2020 relaxes the s.8(3)(ক) and (ঙ) distances to at least 400 m for existing advanced-technology kilns (Hybrid Hoffman, Tunnel) outside the listed areas, on condition that air pollution meets the 1997 standards and the workplace is healthy. A further proviso says it does not apply to establishing new kilns. | A narrow exception for existing HHK/Tunnel kilns. It is not a blanket 400 m rule and does not touch the forest, hill, hill-district, ecologically critical area or degraded air shed restrictions. Do not apply 400 m to detections. | Pending | No |
| Section 8 proviso (2019) | Government may relax other conditions for kilns that existed before commencement if area air standards are met; it excludes s.8(1)(ঙ) and s.8(3)(খ)-(ঘ). | Matches `legal_status_caveat` and `forest_hill_note` in `config/rules.yaml`. Imagery cannot show establishment date, so flags stay candidates. | Pending | No |
| Not implemented: agricultural land, ecologically critical areas, hills, railways, degraded air sheds | s.8(1)(ঘ) agricultural land, (ঙ) ecologically critical areas, (চ) degraded air shed; s.8(3)(গ) 0.5 km from hills; s.8(3)(ঙ) railways; s.5(1) bars taking soil from agricultural land or hills for bricks. | Listed in `not_implemented` in `config/rules.yaml`. No public polygon layer was confirmed for ecologically critical areas; Protected Planet, HDX and the BFIS layer each carry caveats recorded in the dossier. | Pending | No |
| Road distance (none) | No road-distance rule in the Act, the 2019 gazette or the official pages reviewed. | Do not add a road rule without a primary source. The Act names railways, not ordinary roads. | Pending | No |

Do not change a `verified` flag or a numeric threshold based on a secondary
summary, search result, model output, or this template. The application must
continue to label outputs as advisory while any rule remains unverified.

## Open Questions

- Severity values (1-3) are project choices, not legal text. The dossier supports
  distances only.
- Which primary-source passage establishes each configured distance and
  severity?
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

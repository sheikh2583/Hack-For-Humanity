# Screening language and provenance

## Meaning of dashboard signals

The dashboard presents detector outputs as **kiln candidates**. Detector
confidence describes the model's confidence in its class prediction; it is not
a confidence score for a legal conclusion. A candidate rule signal means only
that the pipeline's configured GIS method matched a mapped feature. Neither a
model class nor a spatial buffer establishes a kiln's legal or administrative
status. Screening priority is a ranking heuristic and does not change a
signal's review state. Authority confirmation requires a separate, competent
review.

Distances are computed between the detected kiln geometry and the mapped
feature geometry in the configured projected CRS. They may not be distances to
the legally controlling boundary. Every marker popup carries this advisory,
and CSV exports include it in a preamble and a row field.

## Per-signal provenance record

`signal_provenance_json` is a JSON array on each scored GeoParquet row. Each
signal record includes:

- `signal_id`, `review_state` (generated as `unverified_candidate`), and
  `rule_config_version` plus its config reference;
- source-layer ID, authority, URL, extract version date, and access date;
- feature ID, geometry provenance, measured distance, and method;
- detector checkpoint identity/version, detector confidence, and imagery date;
- legal instrument ID/effective dates where established; and reviewer, review
  date, evidence references, and notes.

The supported review-state vocabulary is `unverified_candidate`,
`human_reviewed`, `authority_confirmed`, and `dismissed`. The repository does
not currently implement a human or authority review workflow. New generated
signals therefore remain `unverified_candidate`; no state transition is
inferred from model confidence or GIS matching.

## Known provenance gaps and required authoritative inputs

- **Legacy OSM caches:** files created before provenance fields were added do
  not carry an extract date or a guaranteed OSM feature ID. The pipeline
  identifies their expected source layer and OSM source, but records unavailable
  feature and snapshot metadata as missing. Refreshing a cache records query
  access time and the returned feature index; it does not establish the
  underlying OSM snapshot date or legal authority of mapped geometry.
- **Imagery dates:** `export_composites` submits a date-range Earth Engine
  composite, but the current GeoTIFF/export contract does not preserve selected
  source-scene dates or a sidecar export manifest. `imagery_date` is therefore
  null. Resolving this requires a manifest from the export step recording the
  Earth Engine collection, selected scene IDs/date range, compositing method,
  export task, and source image dates.
- **Model identity:** inference stores the checkpoint model argument or
  filename and installed Ultralytics version. It does not prove checkpoint
  integrity. A reproducible deployment should additionally preserve the
  checkpoint SHA-256 and training-run manifest ID.
- **Legal instruments:** a rule ID and YAML version do not prove which legal
  provision governs an individual signal. Instrument ID and effective dates
  remain null until a qualified reviewer establishes the mapping and current
  force from official Gazette/legislation sources. Environmental rules
  referenced by the 2020 notification, later wildlife restrictions, and
  licensing changes require legal reconciliation before implementation.
- **Mapped boundaries:** OSM facilities and generic geometry remain screening
  data. Resolving legal distances requires official, current, licensed
  geometries for the exact statutory categories and the legally controlling
  reference boundaries. Required records include: Forest Department government
  forest boundary data with supporting notifications; gazetted ECA and
  sanctuary/national-park polygons from the authorities responsible for those
  designations; Bangladesh Railway's relevant corridor/right-of-way geometry;
  and school/hospital facility boundaries plus settlement boundaries or
  documented family counts from the competent service/local authorities. For
  wetlands, obtain the source and method that establish the Act's seasonal
  submergence definition for each mapped polygon. Confirm each data authority,
  legal basis, geometry, date, and licence before treating it as controlling.
  LGED layers may help screen but are not treated as legally controlling
  without authority and geometry confirmation.
- **Legal updates:** obtain authenticated Gazette/current-law texts and any
  applicable court orders from the official publication/legislative sources.
  A qualified reviewer must reconcile S.R.O. 07-Ain/2020 with subsequent
  environmental rules, determine whether the cited ECR-1997 requirements have
  changed, and review the user-supplied 2026 wildlife and tax-law leads against
  primary texts before implementing anything. The apparent sanctuary/national
  park buffer and tax/licence implications are not encoded as rules here.
- **Administrative status:** authority-confirmed status requires a reliable
  licence/ECC record tied to an individual kiln and validity dates, plus a
  documented competent-authority decision. Obtain the relevant District
  Commissioner's kiln licence register and Department of Environment ECC
  records, with record identifiers, issue/expiry dates, kiln identity matching
  basis, correction history, and permitted reuse terms. No such record or
  review process is present in this repository.

Do not change legal thresholds, technology permissions, or status fields from
these provenance records alone. See [the legal evidence register](legal_basis.md)
and `config/rules.yaml` for the current unverified screening configuration.

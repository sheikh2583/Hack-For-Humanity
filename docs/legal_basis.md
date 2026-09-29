# Legal Basis and Verification Record

**Status:** Draft. No legal threshold in this project is verified.

This document is an evidence register, not legal advice. The values in
`config/rules.yaml` must remain `verified: false` until a person checks the
original Act and gazette text and records the evidence below.

## Sources To Verify

- Brick Manufacturing and Kiln Establishment (Control) Act 2013, including
  amendments. Record the official URL, section, page, and access date here.
- January 2020 gazette concerning advanced-technology kilns. Record the
  official URL, gazette number, section, page, and access date here.
- Any official public kiln or licence register used for validation. Record its
  owner, release date, coverage, field definitions, and licence here.

## Rule Evidence Table

Complete one row for every rule and technology flag in `config/rules.yaml`.

| Config item | Exact source passage | Unit and interpretation | Reviewer/date | Verified? |
|---|---|---|---|---|
| `technology` | Pending primary-source review | Pending | Pending | No |
| `siting_rules` | Pending primary-source review | Pending | Pending | No |
| Any future rule | Pending primary-source review | Pending | Pending | No |

Do not change a `verified` flag or a numeric threshold based on a secondary
summary, search result, model output, or this template. The application must
continue to label outputs as advisory while any rule remains unverified.

## Open Questions

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

import { Candidate } from "./types";

export const FALLBACK_CANDIDATES: Candidate[] = [
  {
    id: "4541f65c-ac90-4dea-a90c-8c6a998625d6",
    district: "Dhaka",
    latitude: 23.76923656463623,
    longitude: 90.41157913208008,
    class: "FCBK",
    confidence: 0.46941086649894714,
    screening_priority: 20.39470133088356,
    priority_rank: 1,
    priority_band: "High",
    candidate_rule_signals: [
      "technology_flagged",
      "near_school",
      "near_hospital",
      "near_settlement"
    ],
    signal_count: 4,
    rules_version: "draft-1",
    advisory: "Advisory only: unverified screening candidates",
    fallback: true
  }
];

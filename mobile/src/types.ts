export type Candidate = {
  id: string;
  district: string;
  latitude: number;
  longitude: number;
  class: string;
  confidence: number;
  screening_priority: number;
  priority_rank: number | null;
  priority_band: string;
  candidate_rule_signals: string[];
  signal_count: number;
  rules_version: string;
  advisory: string;
  fallback?: boolean;
  distance_m?: number;
};

export type CandidateResponse = {
  items: Candidate[];
  count: number;
  source: string;
  modified: string | null;
  advisory: string;
};

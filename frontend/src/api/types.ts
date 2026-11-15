/* Typed payloads mirroring the backend API. */

export type CaseStatus = "open" | "confirmed" | "denied" | "unsure" | "dismissed";
export type RiskTier = "elevated" | "high" | "critical";
export type TemplateStatus = "proposed" | "approved" | "rejected";

export interface CaseListItem {
  id: number;
  payment_id: number;
  user_id: number;
  user_name: string;
  city: string;
  segment: string;
  payment_ts: string;
  amount: number;
  scam_type: string | null;
  payee_id: number;
  is_demo: number;
  payee_handle: string;
  payee_name: string;
  payee_prior_reports: number;
  payee_fan_in: number;
  score: number;
  risk_tier: RiskTier;
  status: CaseStatus;
  checkin_state: string;
  reasons: string[];
  created_at: string;
  answered_at: string | null;
}

export interface GraphNode {
  id: string;
  type: "event" | "stage" | "payment" | "behavior";
  label: string;
  timestamp: string;
  contribution: number;
  stage?: string;
  highlighted: boolean;
  contribution_share: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "time_order" | "supports_stage";
}

export interface CaseGraph {
  case_id: number;
  confidence: number;
  payment_ref: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  top_features: { feature: string; contribution: number; share: number }[];
  reasons: string[];
}

export interface TimelineEvent {
  stage: string;
  ts: string;
  channel: string;
  lang: string;
  text: string;
}

export interface BehaviorEvent {
  kind: string;
  ts: string;
  detail: string;
}

export interface Checkin {
  id: number;
  case_id: number;
  sent_at: string;
  tier: string;
  answer: string | null;
  answered_at: string | null;
}

export interface ReportSummary {
  id: number;
  report_id: string;
  completeness: number;
  status: string;
  reference_id: string | null;
  submitted_at: string | null;
}

export interface FeatureRow {
  payment_id: number;
  new_payee: number; amount_z: number; first_high_value: number;
  hour_of_day: number; is_unusual_hour: number; call_active: number;
  app_switches: number; hesitation_secs: number;
  post_balance_checks: number; post_reversal_search: number;
  post_support_contact: number; post_payee_contact_failed: number;
  fd_break: number; loan_taken: number;
  payee_prior_reports: number; payee_fan_in: number;
  urgency_score: number; authority_score: number; threat_score: number; text_risk: number;
  template_match: number; stage_count: number;
}

export interface CaseDetail extends CaseListItem {
  features: FeatureRow;
  timeline: TimelineEvent[];
  behaviors: BehaviorEvent[];
  checkin: Checkin | null;
  report: ReportSummary | null;
  graph: CaseGraph;
}

export interface ReportPayload {
  report_id: string;
  created_at: string;
  timestamps: Record<string, string | null>;
  payment_refs: { utr: string; upi_ref: string };
  amount: number;
  currency: string;
  payee: { identifier: string; handle: string; name: string; prior_reports: number };
  scam_type: string;
  scam_type_label: string;
  stage_timeline: { stage: string; ts: string; detail: string }[];
  first_contact_channel: string;
  claimed_identity: string;
  urgency_cues: string[];
  communication_identifiers: { caller_number_masked: string; payee_handle: string; languages: string[] };
  evidence: { name: string; kind: string; mock: boolean }[];
  model: { confidence: number; risk_tier: string; reason_codes: string[] };
  customer_confirmation: { status: string; answer_note: string };
  consent: Record<string, boolean>;
  narrative: string;
  llm_used: boolean;
  completeness: number;
  synthetic_data_notice: string;
}

export interface ReportEnvelope {
  id: number;
  report_id: string;
  case_id?: number;
  payload: ReportPayload;
  completeness: number;
  status: string;
  reference_id: string | null;
  submitted_at: string | null;
  created_at: string;
  reused?: boolean;
}

export interface CasesResponse {
  items: CaseListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface CasesSummary {
  open: number;
  confirmed: number;
  denied: number;
  total_flagged: number;
  avg_minutes_to_confirm: number | null;
}

export interface Template {
  id: number;
  name: string;
  scam_type: string;
  hook: string;
  claimed_identity: string;
  urgency_cue: string;
  payment_ask: string;
  channel: string;
  stages: string[];
  script_samples: string[];
  top_terms: string[];
  novelty_score: number;
  status: TemplateStatus;
  size: number;
  created_at: string;
}

export interface BudgetParams {
  c0: number;
  alpha: number;
  window_minutes: number;
  decay: number;
  latency_minutes?: number;
  cooldown_minutes?: number;
}

export interface BudgetResult {
  parameters: Required<BudgetParams>;
  operating_point: {
    payments: number; scams: number; checkins_sent: number; checkins_per_1000: number;
    recall: number; tier_counts: Record<string, number>; c0: number; value_of_delay: number;
  };
  curve: { checkins_per_1000: number; recall: number; c0: number }[];
  baseline_curve: { threshold: number; checkins_per_1000: number; recall: number; checkins_sent: number }[];
  test_window: { start: string; end: string; payments: number; scams: number };
}

export interface Metrics {
  generated_at: string;
  synthetic: boolean;
  banner: string;
  test_window: { start: string; end: string; payments: number; scams: number };
  flag_threshold: number;
  budget_fraction: number;
  model: {
    pr_auc: number;
    recall_at_flag_threshold: number;
    recall_at_fixed_budget: number;
    false_flag_rate_hard_negatives: number;
    checkins_per_1000: number;
    precision_at_flag_threshold: number;
    leave_one_scam_type_out_recall: Record<string, number | null>;
  };
  baselines: {
    rule_based: { recall: number; false_flag_rate_hard_negatives: number; checkins_per_1000: number };
    transaction_only_model: {
      pr_auc: number; recall_at_fixed_budget: number;
      recall_at_flag_threshold: number; checkins_per_1000: number;
    };
  };
  notes: string[];
}

export interface CustomerOverview {
  user: {
    id: number; name: string; segment: string; city: string;
    avg_amount: number; monthly_frequency: number; device_os: string; biometric_enabled: number;
  };
  payments: {
    id: number; ts: string; amount: number; payee_handle: string; payee_name: string;
    is_new_payee: number; call_active: number; scam_type: string | null; is_demo: number;
  }[];
  demo_case_id: number | null;
  synthetic_data: boolean;
}

export interface DemoStory {
  case_id: number;
  payment_id: number;
  user_name: string;
  amount: number;
  payee_handle: string;
  payment_ts: string;
  story: string[];
}

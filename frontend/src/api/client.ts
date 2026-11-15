import type {
  BudgetParams, BudgetResult, CaseDetail, CasesResponse, CasesSummary,
  CustomerOverview, DemoStory, Metrics, ReportEnvelope, CaseListItem, Template,
} from "./types";

const BASE: string = import.meta.env.VITE_API_BASE ?? "http://localhost:8011";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export interface CaseQuery {
  status?: string;
  scam_type?: string;
  min_score?: number;
  q?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  health: () => request<{ status: string; seeded: boolean; version: string; time: string }>("/health"),
  simulate: (body: Partial<{ seed: number; users: number; days: number; scam_rate: number; flag_threshold: number }>) =>
    request<{ ok: boolean; summary: unknown }>("/simulate", { method: "POST", body: JSON.stringify(body) }),

  casesSummary: () => request<CasesSummary>("/cases/summary"),
  listCases: (q: CaseQuery = {}) => {
    const params = new URLSearchParams();
    (Object.entries(q) as [string, string | number | undefined][]).forEach(([k, v]) => {
      if (v !== undefined && v !== "") params.set(k, String(v));
    });
    return request<CasesResponse>(`/cases?${params.toString()}`);
  },
  getCase: (id: number) => request<CaseDetail>(`/cases/${id}`),
  answerCheckin: (id: number, answer: "confirm" | "deny" | "unsure") =>
    request<{ ok: boolean; status: string }>(`/cases/${id}/checkin`, { method: "POST", body: JSON.stringify({ answer }) }),
  requestCallback: (id: number) =>
    request<{ ok: boolean }>(`/cases/${id}/request-callback`, { method: "POST" }),
  dismissCase: (id: number) => request<{ ok: boolean }>(`/cases/${id}/dismiss`, { method: "POST" }),

  createReport: (caseId: number) =>
    request<ReportEnvelope>(`/cases/${caseId}/report`, { method: "POST" }),
  getReport: (id: number) => request<ReportEnvelope>(`/reports/${id}`),
  submitReport: (id: number) =>
    request<{ ok: boolean; reference_id: string; status: string; submitted_at: string; note: string }>(
      `/reports/${id}/submit`, { method: "POST" }),

  templates: (status?: string) =>
    request<{ items: Template[]; total: number }>(`/templates${status ? `?status=${status}` : ""}`),
  approveTemplate: (id: number) =>
    request<{ ok: boolean; status: string }>(`/templates/${id}/approve`, { method: "POST" }),
  rejectTemplate: (id: number) =>
    request<{ ok: boolean; status: string }>(`/templates/${id}/reject`, { method: "POST" }),

  budgetSimulate: (p: Partial<BudgetParams>) =>
    request<BudgetResult>("/budget/simulate", { method: "POST", body: JSON.stringify(p) }),

  metrics: () => request<Metrics>("/metrics"),
  customerOverview: () => request<CustomerOverview>("/customer/overview"),
  demoStory: () => request<DemoStory>("/demo/story", { method: "POST" }),
};

export type { CaseListItem };

export interface JobPosting {
  id: number;
  source: string;
  title: string;
  company: string | null;
  location: string | null;
  url: string;
  salary_text: string | null;
  posted_at: string | null;
  ingested_at: string;
  keyword_match_score: number | null;
  matched_keywords: string[] | null;
  relevance_reasoning: string | null;
}

export interface Application {
  id: number;
  job_posting_id: number;
  company: string | null;
  role_title: string | null;
  source_portal: string | null;
  status: string;
  applied_at: string | null;
  last_status_change_at: string;
  notes: string | null;
}

export interface KeywordFilterItem {
  id: number;
  pipeline: string;
  keyword: string;
  category: "role" | "skill" | null;
  is_active: boolean;
  created_at: string;
}

export interface PipelineSourceItem {
  key: string;
  label: string;
  enabled: boolean;
}

export interface LLMStatus {
  configured_providers: string[];
}

export interface DocumentItem {
  id: number;
  application_id: number;
  doc_type: "resume" | "cover_letter";
  version_number: number;
  generated_at: string;
  content_text: string | null;
  company: string | null;
  role_title: string | null;
  // Only ever populated on the response from generateResume/generateCoverLetter --
  // transient, tells you when this specific generation fell back (LLM unavailable,
  // embeddings not backfilled) instead of looking silently normal.
  warnings?: string[];
}

export interface SkillProfileItem {
  id: number;
  skill_name: string;
  category: string | null;
  proficiency_level: string | null;
  years_experience: number | null;
  evidence_bullet: string | null;
  is_active: boolean;
  sort_order: number;
  updated_at: string;
}

export interface SkillProfileItemInput {
  skill_name: string;
  category?: string | null;
  proficiency_level?: string | null;
  years_experience?: number | null;
  evidence_bullet?: string | null;
}

export interface EducationItem {
  id: number;
  institution: string;
  degree: string;
  field_of_study: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  grade: string | null;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  updated_at: string;
}

export interface WorkExperienceItem {
  id: number;
  company: string;
  role_title: string;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  updated_at: string;
}

export interface ProjectItem {
  id: number;
  title: string;
  description: string | null;
  tech_stack: string | null;
  project_url: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  sort_order: number;
  updated_at: string;
}

export interface CertificationItem {
  id: number;
  name: string;
  issuing_organization: string | null;
  issue_date: string | null;
  credential_url: string | null;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  updated_at: string;
}

// "/api" works in the Codespace/local dev setup because Vite's dev server proxies
// it to the backend on localhost:8000 (see vite.config.ts) -- the browser never
// makes a real cross-origin request. In production the frontend (Vercel) and
// backend (Render) are on different domains with no such proxy, so the deployed
// build needs an absolute URL instead, supplied at build time via Vercel's
// VITE_API_BASE_URL environment variable (see frontend/.env.example).
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// The backend requires HTTP Basic auth on every route except /health (see
// backend/app/core/auth.py) -- entered once via the dashboard's own login
// screen (components/Login.tsx), held only in this browser tab's
// sessionStorage, never in a VITE_-prefixed env var (those get bundled into
// the public JS, which would defeat the entire point).
const AUTH_STORAGE_KEY = "dashboard_auth";

export function getAuthHeader(): string | null {
  return sessionStorage.getItem(AUTH_STORAGE_KEY);
}

export function setAuthHeader(value: string | null): void {
  if (value) sessionStorage.setItem(AUTH_STORAGE_KEY, value);
  else sessionStorage.removeItem(AUTH_STORAGE_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeader = getAuthHeader();
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authHeader ? { Authorization: authHeader } : {}),
    },
    ...init,
  });
  if (res.status === 401) {
    setAuthHeader(null);
    window.location.reload();
    throw new Error("Session expired, please sign in again.");
  }
  if (!res.ok) {
    throw new Error(`${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return res.json();
}

export interface ListMatchesOptions {
  minScore?: number;
  sort?: "score" | "posted_at";
  postedWithinDays?: number;
}

// Education / Experience / Projects / Certifications all follow the identical
// list/create/update(PATCH)/delete shape as skills, just against a different
// /profile/<resource> path -- one factory instead of repeating four times.
function profileCrud<T>(resource: string) {
  return {
    list: () => request<T[]>(`/profile/${resource}`),
    create: (payload: Record<string, unknown>) =>
      request<T>(`/profile/${resource}`, { method: "POST", body: JSON.stringify(payload) }),
    update: (id: number, payload: Record<string, unknown>) =>
      request<T>(`/profile/${resource}/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
    remove: (id: number) => request<{ deleted: boolean }>(`/profile/${resource}/${id}`, { method: "DELETE" }),
  };
}

export const api = {
  listMatches: ({ minScore = 0, sort = "score", postedWithinDays }: ListMatchesOptions = {}) => {
    const params = new URLSearchParams({ min_score: String(minScore), sort });
    if (postedWithinDays !== undefined) params.set("posted_within_days", String(postedWithinDays));
    return request<JobPosting[]>(`/matches?${params.toString()}`);
  },
  listApplications: (status?: string) =>
    request<Application[]>(`/applications${status ? `?status=${status}` : ""}`),
  stageApplication: (jobPostingId: number, notes?: string) =>
    request<Application>("/applications", {
      method: "POST",
      body: JSON.stringify({ job_posting_id: jobPostingId, notes }),
    }),
  updateApplicationStatus: (id: number, status: string, notes?: string) =>
    request<Application>(`/applications/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, notes }),
    }),
  deleteApplication: (id: number) => request<{ deleted: boolean }>(`/applications/${id}`, { method: "DELETE" }),

  generateResume: (applicationId: number, instructions?: string) =>
    request<DocumentItem>(`/applications/${applicationId}/generate_resume`, {
      method: "POST",
      body: JSON.stringify({ instructions: instructions || null }),
    }),
  generateCoverLetter: (applicationId: number, instructions?: string) =>
    request<DocumentItem>(`/applications/${applicationId}/generate_cover_letter`, {
      method: "POST",
      body: JSON.stringify({ instructions: instructions || null }),
    }),
  uploadResume: async (applicationId: number, file: File) => {
    // Not routed through request() -- that helper always sets
    // Content-Type: application/json, which would break this multipart body.
    const formData = new FormData();
    formData.append("file", file);
    const authHeader = getAuthHeader();
    const res = await fetch(`${BASE_URL}/applications/${applicationId}/upload_resume`, {
      method: "POST",
      headers: authHeader ? { Authorization: authHeader } : undefined,
      body: formData,
    });
    if (res.status === 401) {
      setAuthHeader(null);
      window.location.reload();
      throw new Error("Session expired, please sign in again.");
    }
    if (!res.ok) {
      throw new Error(`POST /applications/${applicationId}/upload_resume failed: ${res.status}`);
    }
    return res.json() as Promise<DocumentItem>;
  },
  updateDocumentContent: (id: number, contentText: string) =>
    request<DocumentItem>(`/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ content_text: contentText }),
    }),
  documentPreviewUrl: (id: number) => `${BASE_URL}/documents/${id}/download?inline=true`,
  listDocuments: (applicationId?: number) =>
    request<DocumentItem[]>(`/documents${applicationId !== undefined ? `?application_id=${applicationId}` : ""}`),
  deleteDocument: (id: number) => request<{ deleted: boolean }>(`/documents/${id}`, { method: "DELETE" }),
  deleteOldDocuments: (olderThanDays: number) =>
    request<{ deleted_count: number }>(`/documents?older_than_days=${olderThanDays}`, { method: "DELETE" }),
  documentDownloadUrl: (id: number) => `${BASE_URL}/documents/${id}/download`,

  listSkills: () => request<SkillProfileItem[]>("/profile/skills"),
  createSkill: (payload: SkillProfileItemInput) =>
    request<SkillProfileItem>("/profile/skills", { method: "POST", body: JSON.stringify(payload) }),
  updateSkill: (id: number, payload: Partial<SkillProfileItemInput & { is_active: boolean }>) =>
    request<SkillProfileItem>(`/profile/skills/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteSkill: (id: number) => request<{ deleted: boolean }>(`/profile/skills/${id}`, { method: "DELETE" }),

  education: profileCrud<EducationItem>("education"),
  experience: profileCrud<WorkExperienceItem>("experience"),
  projects: profileCrud<ProjectItem>("projects"),
  certifications: profileCrud<CertificationItem>("certifications"),

  listKeywords: () => request<KeywordFilterItem[]>("/settings/keywords"),
  createKeyword: (payload: { keyword: string; category: "role" | "skill" }) =>
    request<KeywordFilterItem>("/settings/keywords", { method: "POST", body: JSON.stringify(payload) }),
  updateKeyword: (id: number, payload: Partial<{ keyword: string; category: string; is_active: boolean }>) =>
    request<KeywordFilterItem>(`/settings/keywords/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteKeyword: (id: number) => request<{ deleted: boolean }>(`/settings/keywords/${id}`, { method: "DELETE" }),

  listPipelineSources: () => request<PipelineSourceItem[]>("/settings/pipeline_sources"),
  setPipelineSource: (key: string, enabled: boolean) =>
    request<PipelineSourceItem>(`/settings/pipeline_sources/${key}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),

  llmStatus: () => request<LLMStatus>("/settings/llm_status"),
};

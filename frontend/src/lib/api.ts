// ponytail: single fetch wrapper, token injected per-call (different tokens
// per project). Token storage kept in module state; switch to context if the
// app grows multiple token sources.
let currentToken: string | null = null;
let currentAdminToken: string | null = null;

export function setAuthToken(token: string | null) {
  currentToken = token;
}

export function getAuthToken(): string | null {
  return currentToken;
}

export function setAdminToken(token: string | null) {
  currentAdminToken = token;
}

export function getAdminToken(): string | null {
  return currentAdminToken;
}

const ADMIN_STORAGE_KEY = 'casemap.admin_token';

export function hasAdminToken(): boolean {
  if (currentAdminToken) return true;
  if (typeof window === 'undefined') return false;
  return !!window.localStorage.getItem(ADMIN_STORAGE_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = 'ApiError';
  }
}

interface RequestOpts {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT';
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
}

const BASE = '/api/v1';

// ponytail: server's `require_admin` reads the standard Authorization Bearer
// header (not a custom X-Admin-Token), so we reuse Authorization for the
// admin token on the two /projects endpoints that need it. Per-endpoint
// routing keeps admin and project tokens from stomping each other.
const ADMIN_PATHS = new Set<string>(['/projects']);

function tokenForPath(path: string): string | null {
  return ADMIN_PATHS.has(path) ? currentAdminToken : currentToken;
}

function buildUrl(path: string, query?: RequestOpts['query']): string {
  const url = new URL(`${BASE}${path}`, window.location.origin);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }
  return url.pathname + url.search;
}

export async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenForPath(path);
  if (token) headers['Authorization'] = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.formData) {
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  const res = await fetch(buildUrl(path, opts.query), {
    method: opts.method ?? 'GET',
    headers,
    body,
    signal: opts.signal,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (data?.detail) detail = String(data.detail);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) {
    return (await res.json()) as T;
  }
  return (await res.text()) as unknown as T;
}

// ponytail: small helpers around request() to make hooks read like sentences.
export const api = {
  listProjects: () => request<Project[]>('/projects'),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (body: { name: string; llm_provider?: string; llm_model?: string }) =>
    request<ProjectCreated>('/projects', { method: 'POST', body }),

  listSpecs: (projectId: string) => request<SpecOut[]>(`/projects/${projectId}/specs`),
  uploadSpec: (projectId: string, file: File, format?: string) => {
    const fd = new FormData();
    fd.append('file', file);
    if (format) fd.append('format', format);
    return request<SpecCreated>(`/projects/${projectId}/specs`, { method: 'POST', formData: fd });
  },

  listCases: (projectId: string, tag?: string) =>
    request<CaseRecord[]>(`/projects/${projectId}/cases`, { query: { tag } }),
  getCase: (projectId: string, caseId: string) =>
    request<CaseRecord>(`/projects/${projectId}/cases/${caseId}`),
  patchStatus: (projectId: string, caseId: string, body: StatusPatch) =>
    request<{ case_id: string; status: CaseStatus; note: string; updated_at: string }>(
      `/projects/${projectId}/cases/${caseId}/status`,
      { method: 'PATCH', body },
    ),
  getProgress: (projectId: string) => request<ProgressOut>(`/projects/${projectId}/progress`),

  getGraph: (projectId: string, graphId: string) =>
    request<GraphData>(`/projects/${projectId}/graphs/${graphId}/graph.json`),

  bulkImport: (projectId: string, entries: BulkImportEntry[]) =>
    request<{ imported: number }>(`/projects/${projectId}/statuses/import`, {
      method: 'POST',
      body: { entries },
    }),
  bulkExport: (projectId: string) =>
    request<BulkExportEntry[]>(`/projects/${projectId}/statuses/export`),
};

// Re-export types for hooks convenience.
import type {
  BulkExportEntry,
  BulkImportEntry,
  CaseRecord,
  CaseStatus,
  GraphData,
  ProgressOut,
  Project,
  ProjectCreated,
  SpecCreated,
  SpecOut,
  StatusPatch,
} from './types';
export type {
  BulkExportEntry,
  BulkImportEntry,
  CaseRecord,
  CaseStatus,
  GraphData,
  ProgressOut,
  Project,
  ProjectCreated,
  SpecCreated,
  SpecOut,
  StatusPatch,
};

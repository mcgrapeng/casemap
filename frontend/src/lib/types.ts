// Mirror of casemap server Pydantic schemas.
// ponytail: manual sync is fine; server schemas are stable.
// If we add a codegen step, this becomes the only file to delete.

export type CaseStatus =
  | 'pending'
  | 'in_progress'
  | 'passed'
  | 'failed'
  | 'blocked'
  | 'skipped';

export type CaseType = 'positive' | 'negative' | 'edge' | 'security';

export type Source = 'human' | 'ci' | 'import';

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  llm_provider: string | null;
  llm_model: string | null;
}

export interface ProjectCreated extends Project {
  project_api_key: string;
}

export interface SpecOut {
  id: string;
  project_id: string;
  format: string;
  created_at: string;
}

export interface SpecCreated {
  spec_id: string;
  graph_id: string;
  case_count: number;
}

export interface CaseStep {
  step: string;
  expected?: string;
  [key: string]: unknown;
}

export interface CaseRecord {
  id: string;
  graph_id: string;
  project_id: string;
  type: string;
  title: string;
  description: string;
  steps: CaseStep[];
  endpoint_ref: string | null;
  tags: string[];
  status: CaseStatus;
  note: string;
  updated_at: string | null;
}

export interface ProgressOut {
  total: number;
  pending: number;
  in_progress: number;
  passed: number;
  failed: number;
  blocked: number;
  skipped: number;
  completion_pct: number;
}

export interface StatusPatch {
  status: CaseStatus;
  note?: string;
  source?: Source;
}

export interface BulkImportEntry {
  case_id: string;
  status: CaseStatus;
  note?: string;
  updated_at?: string;
  source?: Source;
}

export interface BulkExportEntry {
  case_id: string;
  status: CaseStatus;
  note: string;
  updated_at: string;
  source: Source;
}

// Layout node from server's brain-map graph.json (subset we render).
export interface GraphNode {
  id: string;
  type: string;
  title: string;
  tags: string[];
  column?: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

export interface GraphEdge {
  from: string;
  to: string;
  label?: string;
}

export interface GraphData {
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
    width?: number;
    height?: number;
  };
  statuses: Record<string, { status: CaseStatus; note: string }>;
}

export interface SpecDetail {
  id: string;
  project_id: string;
  format: string;
  created_at: string;
  graph_id: string | null;
  case_count: number;
}

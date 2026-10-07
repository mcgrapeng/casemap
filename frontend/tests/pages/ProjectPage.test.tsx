import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProjectPage from '@/pages/ProjectPage';
import { AuthProvider } from '@/components/providers/ApiProvider';
import { ThemeProvider } from '@/hooks/useTheme';
import { ToastRoot } from '@/hooks/useToast';

vi.mock('@/lib/api', () => ({
  api: {
    getProject: vi.fn(),
    listSpecs: vi.fn(),
    listCases: vi.fn(),
    getProgress: vi.fn(),
    getGraph: vi.fn(),
    listProjects: vi.fn(),
    createProject: vi.fn(),
    getCase: vi.fn(),
    patchStatus: vi.fn(),
    bulkImport: vi.fn(),
    bulkExport: vi.fn(),
    uploadSpec: vi.fn(),
  },
  setAuthToken: vi.fn(),
  getAuthToken: vi.fn(),
  setAdminToken: vi.fn(),
  getAdminToken: vi.fn(),
  ApiError: class ApiError extends Error {
    status = 0;
    detail = '';
  },
}));

import * as api from '@/lib/api';

const mockedGetProject = api.api.getProject as ReturnType<typeof vi.fn>;
const mockedListSpecs = api.api.listSpecs as ReturnType<typeof vi.fn>;
const mockedListCases = api.api.listCases as ReturnType<typeof vi.fn>;
const mockedGetProgress = api.api.getProgress as ReturnType<typeof vi.fn>;
const mockedGetGraph = api.api.getGraph as ReturnType<typeof vi.fn>;

function renderProject(initialEntries: string[] = ['/projects/proj-1']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider>
        <AuthProvider>
          <ToastRoot>
            <MemoryRouter initialEntries={initialEntries}>
              <Routes>
                <Route path="/projects/:id" element={<ProjectPage />} />
              </Routes>
            </MemoryRouter>
          </ToastRoot>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.setItem('casemap-token', 'test-token');
  mockedGetProject.mockResolvedValue({
    id: 'proj-1',
    name: 'Acme API',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    llm_provider: null,
    llm_model: null,
  });
  mockedListSpecs.mockResolvedValue([
    {
      id: 'spec-1',
      project_id: 'proj-1',
      format: 'openapi',
      created_at: '2024-01-01T00:00:00Z',
    },
  ]);
  mockedListCases.mockResolvedValue([
    {
      id: 'case-1',
      graph_id: 'spec-1',
      project_id: 'proj-1',
      type: 'positive',
      title: 'Sign in works',
      description: 'desc',
      steps: [],
      endpoint_ref: 'POST /auth/login',
      tags: ['auth'],
      status: 'pending',
      note: '',
      updated_at: null,
    },
  ]);
  mockedGetProgress.mockResolvedValue({
    total: 1,
    pending: 1,
    in_progress: 0,
    passed: 0,
    failed: 0,
    blocked: 0,
    skipped: 0,
    completion_pct: 0,
  });
  mockedGetGraph.mockResolvedValue({
    graph: {
      nodes: [
        {
          id: 'case-1',
          type: 'positive',
          title: 'Sign in works',
          tags: ['auth'],
          x: 0,
          y: 0,
          width: 160,
          height: 48,
        },
      ],
      edges: [],
      width: 600,
      height: 400,
    },
    statuses: { 'case-1': { status: 'pending', note: '' } },
  });
});

describe('<ProjectPage />', () => {
  it('renders project name after load', async () => {
    renderProject();
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Acme API/ })).toBeInTheDocument();
    });
  });

  it('shows the brain map SVG', async () => {
    renderProject();
    await waitFor(() => {
      expect(screen.getByTestId('brain-map-svg')).toBeInTheDocument();
    });
  });
});

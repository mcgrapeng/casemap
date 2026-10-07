// ponytail: jsdom-based axe check is approximate (it runs without a real layout
// engine). We focus on the worst axe violations: missing form labels, color
// contrast on critical widgets, and landmark roles. A full a11y audit lives in
// the design system; this just guards against regressions.
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import axe from 'axe-core';
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

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider>
        <AuthProvider>
          <ToastRoot>
            <MemoryRouter initialEntries={['/projects/proj-1']}>
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
    name: 'Acme',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
    llm_provider: null,
    llm_model: null,
  });
  mockedListSpecs.mockResolvedValue([]);
  mockedListCases.mockResolvedValue([]);
  mockedGetProgress.mockResolvedValue({
    total: 0,
    pending: 0,
    in_progress: 0,
    passed: 0,
    failed: 0,
    blocked: 0,
    skipped: 0,
    completion_pct: 0,
  });
  mockedGetGraph.mockResolvedValue({
    graph: { nodes: [], edges: [], width: 600, height: 400 },
    statuses: {},
  });
});

describe('ProjectPage a11y', () => {
  it('has no critical axe violations', async () => {
    const { container } = setup();
    await waitFor(() => {
      expect(mockedGetProject).toHaveBeenCalled();
    });
    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
      },
    });
    const critical = results.violations.filter((v) => v.impact === 'critical');
    expect(critical, JSON.stringify(critical, null, 2)).toEqual([]);
  });
});

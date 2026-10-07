import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api');
  return {
    ...actual,
    api: {
      listProjects: vi.fn(),
      getProject: vi.fn(),
      createProject: vi.fn(),
    },
  };
});

import { api } from '@/lib/api';
import { useProjects } from '@/hooks/useProjects';

const mockedListProjects = api.listProjects as ReturnType<typeof vi.fn>;

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

beforeEach(() => {
  window.localStorage.removeItem('casemap.admin_token');
  mockedListProjects.mockReset();
});

afterEach(() => {
  window.localStorage.removeItem('casemap.admin_token');
});

describe('useProjects', () => {
  it('does not fetch when no admin token is in localStorage', () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockedListProjects.mockResolvedValue([]);

    renderHook(() => useProjects(), { wrapper: makeWrapper(qc) });

    expect(mockedListProjects).not.toHaveBeenCalled();
  });

  it('fetches when an admin token is in localStorage', async () => {
    window.localStorage.setItem('casemap.admin_token', 'mysecret');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockedListProjects.mockResolvedValue([]);

    renderHook(() => useProjects(), { wrapper: makeWrapper(qc) });

    // Let any pending microtasks flush.
    await Promise.resolve();
    expect(mockedListProjects).toHaveBeenCalledTimes(1);
  });

  it('does not retry after a 401', async () => {
    window.localStorage.setItem('casemap.admin_token', 'mysecret');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockedListProjects.mockRejectedValue(new Error('401 Unauthorized'));

    renderHook(() => useProjects(), { wrapper: makeWrapper(qc) });

    await Promise.resolve();
    expect(mockedListProjects).toHaveBeenCalledTimes(1);
  });
});

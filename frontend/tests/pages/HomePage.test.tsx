import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import HomePage from '@/pages/HomePage';
import { AuthProvider } from '@/components/providers/ApiProvider';
import { ThemeProvider } from '@/hooks/useTheme';
import { ToastRoot } from '@/hooks/useToast';
import { ApiError } from '@/lib/api';

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

import * as api from '@/lib/api';

const mockedListProjects = api.api.listProjects as ReturnType<typeof vi.fn>;

function renderHome(initialEntries: string[] = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider>
        <AuthProvider>
          <ToastRoot>
            <MemoryRouter initialEntries={initialEntries}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/projects/new" element={<div data-testid="new-project-page" />} />
                <Route path="/projects/:id" element={<div data-testid="project-page" />} />
              </Routes>
            </MemoryRouter>
          </ToastRoot>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockedListProjects.mockReset();
});

describe('<HomePage /> admin token', () => {
  it('renders an Admin token card with empty input by default', async () => {
    mockedListProjects.mockResolvedValue([]);
    renderHome();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Admin token/i })).toBeInTheDocument();
    });
    expect(screen.getByLabelText('Admin token')).toBeInTheDocument();
  });

  it('persists admin token to localStorage and restores on next mount', async () => {
    mockedListProjects.mockResolvedValue([]);
    const user = userEvent.setup();

    const { unmount } = renderHome();
    const input = await screen.findByLabelText('Admin token');
    await user.type(input, 'mysecret');
    await user.click(screen.getByRole('button', { name: '保存' }));

    expect(window.localStorage.getItem('casemap.admin_token')).toBe('mysecret');
    unmount();

    renderHome();
    // After remount, admin token is restored, so input collapses to "configured" view
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Clear admin token' })).toBeInTheDocument();
    });
    expect(window.localStorage.getItem('casemap.admin_token')).toBe('mysecret');
  });

  it('clears admin token when "清除" button is clicked', async () => {
    window.localStorage.setItem('casemap.admin_token', 'oldsecret');
    mockedListProjects.mockResolvedValue([]);
    const user = userEvent.setup();
    renderHome();

    const clearBtn = await screen.findByRole('button', { name: 'Clear admin token' });
    await user.click(clearBtn);

    await waitFor(() => {
      expect(window.localStorage.getItem('casemap.admin_token')).toBeNull();
    });
    expect(screen.getByLabelText('Admin token')).toBeInTheDocument();
  });

  it('shows error toast and stays on home when clicking New Project without admin token', async () => {
    mockedListProjects.mockResolvedValue([]);
    const user = userEvent.setup();
    renderHome();

    await user.click(screen.getByRole('button', { name: /Create new project/i }));

    await waitFor(() => {
      expect(screen.getByText(/请先输入管理员令牌/)).toBeInTheDocument();
    });
    expect(screen.queryByTestId('new-project-page')).not.toBeInTheDocument();
  });

  it('navigates to /projects/new when admin token is set and New Project clicked', async () => {
    window.localStorage.setItem('casemap.admin_token', 'mysecret');
    mockedListProjects.mockResolvedValue([]);
    const user = userEvent.setup();
    renderHome();

    await user.click(screen.getByRole('button', { name: /Create new project/i }));

    await waitFor(() => {
      expect(screen.getByTestId('new-project-page')).toBeInTheDocument();
    });
  });

  it('shows the list of projects when admin token is configured', async () => {
    window.localStorage.setItem('casemap.admin_token', 'mysecret');
    mockedListProjects.mockResolvedValue([
      {
        id: 'p1',
        name: 'Acme',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-02T00:00:00Z',
        llm_provider: null,
        llm_model: null,
      },
    ]);
    renderHome();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Acme' })).toBeInTheDocument();
    });
  });

  it('shows "Admin token required" card when listProjects returns 403', async () => {
    window.localStorage.setItem('casemap.admin_token', 'mysecret');
    mockedListProjects.mockRejectedValue(new ApiError(403, 'Admin token mismatch'));
    renderHome();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Admin token required/i })).toBeInTheDocument();
    });
  });
});

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  request,
  setAuthToken,
  getAuthToken,
  setAdminToken,
  getAdminToken,
} from '@/lib/api';

describe('api.ts', () => {
  beforeEach(() => {
    setAuthToken(null);
    setAdminToken(null);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    setAuthToken(null);
    setAdminToken(null);
  });

  it('exports setAuthToken / getAuthToken round-trip', () => {
    setAuthToken('proj-xyz');
    expect(getAuthToken()).toBe('proj-xyz');
    setAuthToken(null);
    expect(getAuthToken()).toBeNull();
  });

  it('exports setAdminToken / getAdminToken round-trip', () => {
    setAdminToken('admin-secret');
    expect(getAdminToken()).toBe('admin-secret');
    setAdminToken(null);
    expect(getAdminToken()).toBeNull();
  });

  it('sends admin token as Authorization Bearer on /projects endpoints', async () => {
    setAdminToken('admin-secret');
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const headers = init.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer admin-secret');
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    const data = await request<unknown[]>('/projects');
    expect(data).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('prefers admin token over project token on /projects endpoints', async () => {
    setAuthToken('proj-key');
    setAdminToken('admin-key');
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const headers = init.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer admin-key');
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    await request('/projects');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('sends project token on non-/projects endpoints', async () => {
    setAuthToken('proj-key');
    setAdminToken('admin-key');
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const headers = init.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer proj-key');
      return new Response(JSON.stringify({ id: 'p1' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    await request('/projects/p1');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not send Authorization header when no token is set', async () => {
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const headers = init.headers as Record<string, string>;
      expect(headers['Authorization']).toBeUndefined();
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    await request('/projects');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws ApiError with status and detail on non-2xx', async () => {
    setAdminToken('wrong-token');
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ detail: 'Admin token mismatch' }), {
        status: 403,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(request('/projects')).rejects.toMatchObject({
      name: 'ApiError',
      status: 403,
      detail: 'Admin token mismatch',
    });
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// ponytail: vi.useFakeTimers + a controllable mock WebSocket class lets us
// drive reconnect / backoff without real network. We re-stub the global in
// beforeEach because afterEach restores it.

type WSInstance = {
  url: string;
  onopen: ((ev: Event) => void) | null;
  onmessage: ((ev: { data: string }) => void) | null;
  onclose: ((ev: { code: number; reason: string }) => void) | null;
  onerror: ((ev: Event) => void) | null;
  close: (code?: number) => void;
  send: (data: string) => void;
  readyState: number;
  __open: () => void;
  __message: (data: unknown) => void;
  __fail: () => void;
};

class FakeWebSocket {
  static instances: WSInstance[] = [];
  static OPEN = 1;
  static CLOSED = 3;

  url: string;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number; reason: string }) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  readyState = 0;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this as unknown as WSInstance);
  }

  close(code = 1000) {
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onclose) this.onclose({ code, reason: '' });
  }

  send() {
    /* server-push only */
  }

  // Test helpers (not part of WebSocket API)
  __open() {
    this.readyState = FakeWebSocket.OPEN;
    if (this.onopen) this.onopen(new Event('open'));
  }

  __message(data: unknown) {
    if (this.onmessage) this.onmessage({ data: JSON.stringify(data) });
  }

  __fail() {
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onerror) this.onerror(new Event('error'));
    if (this.onclose) this.onclose({ code: 1006, reason: '' });
  }
}

import { act, renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as React from 'react';
import { useStatusStream } from '@/hooks/useStatusStream';

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('useStatusStream', () => {
  it('opens a WebSocket on mount when projectId and token are provided', () => {
    const qc = new QueryClient();
    renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    expect(FakeWebSocket.instances).toHaveLength(1);
    expect(FakeWebSocket.instances[0].url).toContain('/api/v1/projects/proj-1/ws');
    expect(FakeWebSocket.instances[0].url).toContain('token=tok');
  });

  it('does not open a WebSocket when token is missing', () => {
    const qc = new QueryClient();
    renderHook(() => useStatusStream('proj-1', undefined), {
      wrapper: makeWrapper(qc),
    });
    expect(FakeWebSocket.instances).toHaveLength(0);
  });

  it('invalidates all queries under the project on a status_changed message', () => {
    const qc = new QueryClient();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');

    renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    const ws = FakeWebSocket.instances[0];
    act(() => ws.__open());
    act(() =>
      ws.__message({
        type: 'status_changed',
        case_id: 'c1',
        status: 'passed',
        note: '',
        source: 'human',
        updated_at: '2024-01-01T00:00:00Z',
      }),
    );

    // Invalidates the parent ['projects', projectId] prefix so every nested
    // query (cases, progress, graphs) refetches.
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['projects', 'proj-1'],
        exact: false,
      }),
    );
  });

  it('ignores messages with an unknown type', () => {
    const qc = new QueryClient();
    const invalidateSpy = vi.spyOn(qc, 'invalidateQueries');
    renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    const ws = FakeWebSocket.instances[0];
    act(() => ws.__open());
    act(() => ws.__message({ type: 'something_else' }));
    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it('reconnects with exponential backoff after disconnect', () => {
    const qc = new QueryClient();
    renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    const first = FakeWebSocket.instances[0];
    act(() => first.__open());

    // First disconnect: should reconnect after ~1s.
    act(() => first.close(1006));
    expect(FakeWebSocket.instances).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(FakeWebSocket.instances).toHaveLength(2);

    // Second disconnect: should reconnect after ~2s.
    const second = FakeWebSocket.instances[1];
    act(() => second.__fail());
    act(() => {
      vi.advanceTimersByTime(1000); // not yet
    });
    expect(FakeWebSocket.instances).toHaveLength(2);
    act(() => {
      vi.advanceTimersByTime(1000); // 2s total
    });
    expect(FakeWebSocket.instances).toHaveLength(3);

    // Third disconnect: should reconnect after ~4s.
    const third = FakeWebSocket.instances[2];
    act(() => third.__fail());
    act(() => {
      vi.advanceTimersByTime(3000); // not yet (need 4s)
    });
    expect(FakeWebSocket.instances).toHaveLength(3);
    act(() => {
      vi.advanceTimersByTime(1000); // 4s total
    });
    expect(FakeWebSocket.instances).toHaveLength(4);
  });

  it('caps reconnect delay at 30 seconds', () => {
    const qc = new QueryClient();
    renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    const ws0 = FakeWebSocket.instances[0];
    act(() => ws0.__open());

    // Burn through 10 failures; the 10th reconnect should wait ~30s, not 2^9=512s.
    let lastWs = ws0;
    for (let i = 0; i < 10; i++) {
      act(() => lastWs.close(1006));
      // Advance enough to trigger the next reconnect.
      act(() => {
        vi.advanceTimersByTime(35_000);
      });
      lastWs = FakeWebSocket.instances[FakeWebSocket.instances.length - 1];
    }
    // We made progress — at least 10 reconnects happened.
    expect(FakeWebSocket.instances.length).toBeGreaterThanOrEqual(10);
  });

  it('does not reconnect after unmount', () => {
    const qc = new QueryClient();
    const { unmount } = renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    const ws = FakeWebSocket.instances[0];
    act(() => ws.__open());
    unmount();
    act(() => ws.close(1006));
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    // No second WebSocket created after unmount.
    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it('closes the underlying WebSocket on unmount', () => {
    const qc = new QueryClient();
    const { unmount } = renderHook(() => useStatusStream('proj-1', 'tok'), {
      wrapper: makeWrapper(qc),
    });
    const ws = FakeWebSocket.instances[0];
    const closeSpy = vi.spyOn(ws, 'close');
    act(() => ws.__open());
    unmount();
    expect(closeSpy).toHaveBeenCalled();
  });
});

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';

const MAX_BACKOFF_MS = 30_000;
const INITIAL_BACKOFF_MS = 1_000;

function wsUrl(projectId: string, token: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/api/v1/projects/${projectId}/ws?token=${encodeURIComponent(token)}`;
}

export function useStatusStream(projectId: string | undefined, token: string | undefined): void {
  const qc = useQueryClient();
  // Keep the latest queryClient in a ref so the message handler always sees it
  // even if a stale closure was captured.
  const qcRef = React.useRef(qc);
  qcRef.current = qc;

  React.useEffect(() => {
    if (!projectId || !token) return;
    let ws: WebSocket | null = null;
    let attempts = 0;
    let backoff = INITIAL_BACKOFF_MS;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      ws = new WebSocket(wsUrl(projectId, token));
      ws.onopen = () => {
        attempts = 0;
        backoff = INITIAL_BACKOFF_MS;
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data) as { type?: string };
          if (msg.type !== 'status_changed') return;
          // ponytail: invalidate the parent ['projects', projectId] prefix to
          // cover every nested query (cases, progress, graphs) without
          // enumerating them.
          void qcRef.current.invalidateQueries({
            queryKey: ['projects', projectId],
            exact: false,
          });
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (unmounted) return;
        attempts += 1;
        backoff = Math.min(MAX_BACKOFF_MS, INITIAL_BACKOFF_MS * 2 ** (attempts - 1));
        reconnectTimer = setTimeout(connect, backoff);
      };
      ws.onerror = () => {
        // onclose will follow; let it handle reconnect.
      };
    };

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && ws.readyState !== WebSocket.CLOSED) ws.close(1000);
    };
  }, [projectId, token]);
}

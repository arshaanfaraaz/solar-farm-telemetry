import { useCallback, useEffect, useRef, useState } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Manages a WebSocket connection with automatic reconnection.
 * - Reconnects after 3 s on disconnect or error.
 * - Accumulates incidents locally (backend only pushes new ones per tick).
 * - Returns the latest telemetry payload and the full incident log.
 */
export function useWebSocket() {
  const [data, setData] = useState(null);       // latest { telemetry, anomalies, incident }
  const [connected, setConnected] = useState(false);
  const [incidents, setIncidents] = useState([]); // growing list, newest first

  const wsRef = useRef(null);
  const retryRef = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      clearTimeout(retryRef.current);
    };

    ws.onclose = () => {
      setConnected(false);
      retryRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      setData(payload);

      if (payload.incident) {
        setIncidents((prev) => {
          const already = prev.some((i) => i.id === payload.incident.id);
          if (already) return prev;
          return [payload.incident, ...prev].slice(0, 50);
        });
      }
    };
  }, []);

  // Backfill historical incidents from REST on mount so the log is complete
  // regardless of when the frontend connects relative to the backend.
  useEffect(() => {
    fetch(`${API_URL}/incidents`)
      .then((r) => r.json())
      .then((historical) => {
        if (historical.length) setIncidents(historical.slice(0, 50));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, connected, incidents };
}

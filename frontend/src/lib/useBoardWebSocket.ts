import { useEffect, useRef, useCallback } from 'react';

export interface WebSocketEvent {
  type: string;
  card_id?: number;
  source_column_id?: number;
  target_column_id?: number;
  target_order?: number;
  column_id?: number;
  item_id?: number;
  is_completed?: boolean;
  is_self?: boolean;
  board_id?: number;
  user_id?: number;
  [key: string]: unknown;
}

export function useBoardWebSocket(
  boardId: number | null,
  onEvent: (event: WebSocketEvent) => void
) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef<boolean>(true);
  const onEventRef = useRef(onEvent);
  const connectRef = useRef<() => void>(() => {});

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const connect = useCallback(() => {
    if (!boardId || typeof window === 'undefined') return;

    // Build WebSocket URL matching current host
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = `${window.location.hostname}:8080`;
    const token = localStorage.getItem('kanban_token') || '';
    const url = `${protocol}//${host}/ws/boards/${boardId}/?token=${encodeURIComponent(token)}`;

    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data: WebSocketEvent = JSON.parse(event.data);
          if (onEventRef.current) {
            onEventRef.current(data);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        if (isMountedRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connectRef.current();
          }, 3000);
        }
      };

      ws.onerror = () => {
        // Will trigger onclose and attempt reconnect
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
    }
  }, [boardId]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendEvent = useCallback((event: WebSocketEvent) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(event));
    }
  }, []);

  return { sendEvent };
}

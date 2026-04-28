import { useState, useEffect, useRef, useCallback } from 'react';

export type ExecutionEventType =
  | 'scan.started' | 'market.filtered' | 'market.analyzing'
  | 'market.analyzed' | 'market.decided' | 'bet.recorded'
  | 'bet.alert_sent' | 'portfolio.resolved' | 'scan.completed'
  | 'scan.error' | 'connected';

export interface ExecutionEvent {
  type: ExecutionEventType;
  market_id?: string;
  question?: string;
  message: string;
  data: Record<string, unknown>;
  timestamp: string;
}

type ScanStatus = 'idle' | 'running' | 'error';

const MAX_EVENTS = 500;
const BASE_DELAY = 1000;
const MAX_DELAY = 15000;

export function useExecutionFeed(wsUrl = '/api/executions/live') {
  const [events, setEvents] = useState<ExecutionEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [scanStatus, setScanStatus] = useState<ScanStatus>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelayRef = useRef(BASE_DELAY);
  const retryTimerRef = useRef<number | null>(null);
  const isUnmountedRef = useRef(false);

  const addEvent = useCallback((event: ExecutionEvent) => {
    setEvents(prev => {
      const next = [...prev, event];
      return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
    });

    if (event.type === 'scan.started') setScanStatus('running');
    else if (event.type === 'scan.completed' || event.type === 'scan.error') {
      setTimeout(() => { if (!isUnmountedRef.current) setScanStatus('idle'); }, 3000);
    }
  }, []);

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryDelayRef.current = BASE_DELAY;
      };

      ws.onmessage = (evt) => {
        try {
          const event = JSON.parse(evt.data) as ExecutionEvent;
          addEvent(event);
        } catch { /* ignore parse errors */ }
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;

        if (!isUnmountedRef.current) {
          retryTimerRef.current = window.setTimeout(() => {
            retryDelayRef.current = Math.min(retryDelayRef.current * 2, MAX_DELAY);
            connect();
          }, retryDelayRef.current);
        }
      };
    } catch {
      if (!isUnmountedRef.current) {
        retryTimerRef.current = window.setTimeout(connect, retryDelayRef.current);
      }
    }
  }, [wsUrl, addEvent]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();
    return () => {
      isUnmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, isConnected, scanStatus };
}

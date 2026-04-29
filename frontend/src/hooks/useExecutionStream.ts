import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:8080';
const MAX_STEPS = 1000;
const BASE_DELAY = 1000;
const MAX_DELAY = 15000;

export interface StreamStep {
  seq: number;
  step_type: string;
  content: string | null;
  tool_name: string | null;
  tool_input: Record<string, unknown> | null;
  tool_output: string | null;
}

export interface ExecutionStep {
  id: string;
  seq: number;
  step_type: string;
  content: string | null;
  tool_name: string | null;
  tool_input: unknown;
  tool_output: string | null;
  duration_ms: number | null;
}

export function useExecutionStream(executionId: string | null) {
  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelayRef = useRef(BASE_DELAY);
  const retryTimerRef = useRef<number | null>(null);
  const isUnmountedRef = useRef(false);
  const seenSeqsRef = useRef(new Set<number>());

  const connect = useCallback(() => {
    if (!executionId || isUnmountedRef.current) return;

    try {
      const wsUrl = `${API_BASE}/api/executions/${executionId}/stream`.replace('http://', 'ws://');
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        retryDelayRef.current = BASE_DELAY;
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'step') {
            const step: StreamStep = msg;
            if (!seenSeqsRef.current.has(step.seq)) {
              seenSeqsRef.current.add(step.seq);
              setSteps(prev => {
                const next = [
                  ...prev,
                  {
                    id: `${executionId}-${step.seq}`,
                    seq: step.seq,
                    step_type: step.step_type,
                    content: step.content,
                    tool_name: step.tool_name,
                    tool_input: step.tool_input,
                    tool_output: step.tool_output,
                    duration_ms: null,
                  } as ExecutionStep,
                ];
                return next.length > MAX_STEPS ? next.slice(-MAX_STEPS) : next;
              });
            }
          }
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
  }, [executionId]);

  useEffect(() => {
    if (!executionId) {
      setSteps([]);
      return;
    }

    isUnmountedRef.current = false;
    seenSeqsRef.current = new Set();

    fetch(`${API_BASE}/api/executions/${executionId}/steps`)
      .then(res => res.json())
      .then((data: ExecutionStep[]) => {
        if (!isUnmountedRef.current && Array.isArray(data)) {
          data.forEach(s => seenSeqsRef.current.add(s.seq));
          setSteps(data);
        }
        connect();
      })
      .catch(() => {
        connect();
      });

    return () => {
      isUnmountedRef.current = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      wsRef.current?.close();
    };
  }, [executionId, connect]);

  return { steps, isConnected };
}

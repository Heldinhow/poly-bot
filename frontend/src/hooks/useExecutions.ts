import { useQuery } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8080';

export interface Execution {
  id: string;
  task_id: string;
  market_id: string;
  agent_id: string;
  runtime: string;
  model: string | null;
  status: string;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  probability: number | null;
  confidence: number | null;
  reasoning: string | null;
  error_message: string | null;
  failure_reason: string | null;
  input_tokens: number;
  output_tokens: number;
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
  created_at: string;
}

async function fetchExecutions(): Promise<Execution[]> {
  const res = await fetch(`${API_BASE}/api/executions?limit=100`);
  if (!res.ok) throw new Error('Failed to fetch executions');
  return res.json();
}

async function fetchExecutionSteps(logId: string): Promise<ExecutionStep[]> {
  const res = await fetch(`${API_BASE}/api/executions/${logId}/steps`);
  if (!res.ok) throw new Error('Failed to fetch execution steps');
  return res.json();
}

export function useExecutions() {
  const { data: executions, isLoading, error } = useQuery({
    queryKey: ['executions'],
    queryFn: fetchExecutions,
    refetchInterval: 5000,
  });

  return { executions, isLoading, error };
}

export function useExecutionSteps(logId: string | null) {
  const { data: steps, isLoading, error } = useQuery({
    queryKey: ['execution-steps', logId],
    queryFn: () => fetchExecutionSteps(logId!),
    enabled: !!logId,
    refetchInterval: 5000,
  });

  return { steps, isLoading, error };
}

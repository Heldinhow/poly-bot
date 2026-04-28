import { useQuery } from '@tanstack/react-query';
import { fetchAuditSummary, fetchMarketAudit, AuditSummaryParams, MarketAuditResponse } from '@/lib/api';

const API_BASE = 'http://localhost:8080';

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

async function fetchExecutionSteps(logId: string): Promise<ExecutionStep[]> {
  const res = await fetch(`${API_BASE}/api/executions/${logId}/steps`);
  if (!res.ok) throw new Error('Failed to fetch execution steps');
  return res.json();
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

export function useAuditSummary(params: AuditSummaryParams) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit-summary', params],
    queryFn: () => fetchAuditSummary(params),
    staleTime: 30000,
  });

  return { data, isLoading, error };
}

export function useMarketAudit(marketId: string | null): { data: MarketAuditResponse | undefined; isLoading: boolean; error: unknown } {
  const { data, isLoading, error } = useQuery({
    queryKey: ['market-audit', marketId],
    queryFn: () => fetchMarketAudit(marketId!),
    enabled: !!marketId,
    staleTime: 30000,
  });

  return { data, isLoading, error };
}

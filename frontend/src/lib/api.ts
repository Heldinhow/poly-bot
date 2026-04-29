const API_BASE = 'http://localhost:8080';

export interface Stats {
  bankroll: number;
  initial_bankroll: number;
  roi_pct: number;
  realized_pnl: number;
  total_staked_resolved: number;
  realized_roi: number;
  total_bets: number;
  open_bets: number;
  resolved_bets: number;
  wins: number;
  losses: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  underdog_hit_rate: number;
  ai_bets: number;
}

export interface Bet {
  id: number;
  market_id: string;
  question: string;
  outcome: string;
  price: number;
  stake: number;
  payout: number;
  edge: number;
  probability_ai: number | null;
  timestamp: string;
  resolved: boolean;
  result: 'win' | 'lose' | null;
  resolved_at: string | null;
  trading_mode: 'paper' | 'live';
}

export interface TimeseriesPoint {
  date: string;
  bankroll: number;
}

export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, options);
  } catch (err) {
    throw new Error(
      err instanceof Error ? `Network error: ${err.message}` : 'Network error'
    );
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new Error('Invalid JSON response');
  }
}

export async function fetchStats(): Promise<Stats> {
  return apiFetch<Stats>(`${API_BASE}/api/stats`);
}

export async function fetchOpenBets(): Promise<Bet[]> {
  return apiFetch<Bet[]>(`${API_BASE}/api/bets/open`);
}

export async function fetchResolvedBets(limit = 50): Promise<Bet[]> {
  return apiFetch<Bet[]>(`${API_BASE}/api/bets/resolved?limit=${limit}`);
}

export async function fetchTimeseries(days = 30): Promise<TimeseriesPoint[]> {
  return apiFetch<TimeseriesPoint[]>(
    `${API_BASE}/api/bets/timeseries?days=${days}`
  );
}

// Audit types
export interface AuditSummaryParams {
  decision?: string;
  since?: string;
  bet_result?: string;
  cursor?: string;
}

export interface AuditMarket {
  market_id: string;
  question: string;
  yes_price_at_analysis: number;
  no_price_at_analysis: number;
  probabilities: number[];
  confidences: number[];
  reasoning_summary: string;
  decision: string;
  reject_reason: string | null;
  edge: number;
  bet_id: number | null;
  stake: number | null;
  outcome: string | null;
  execution_count: number;
  first_execution_id: string | null;
  last_execution_id: string | null;
}

export interface AuditSummaryResponse {
  items: AuditMarket[];
  next_cursor: string | null;
}

export interface DecisionFactor {
  implied_probability: number;
  ai_probability: number;
  odds: number;
  edge: number;
  decision: string;
  reject_reason: string | null;
  stake: number | null;
  kelly_fraction: number | null;
}

export interface TruthClaim {
  content: string;
  source_reference: string | null;
  confidence_weight: number;
  order_index: number;
}

export interface MarketAuditResponse {
  summary: AuditMarket;
  decision_factors: DecisionFactor[];
  truth_claims: TruthClaim[];
}

export async function fetchAuditSummary(params: AuditSummaryParams): Promise<AuditSummaryResponse> {
  const qs = new URLSearchParams();
  if (params.decision) qs.set('decision', params.decision);
  if (params.since) qs.set('since', params.since);
  if (params.bet_result) qs.set('bet_result', params.bet_result);
  if (params.cursor) qs.set('cursor', params.cursor);
  return apiFetch<AuditSummaryResponse>(`${API_BASE}/api/audit/summary?${qs}`);
}

export async function fetchMarketAudit(marketId: string): Promise<MarketAuditResponse> {
  return apiFetch<MarketAuditResponse>(`${API_BASE}/api/audit/market/${encodeURIComponent(marketId)}`);
}

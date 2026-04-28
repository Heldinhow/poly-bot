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

async function apiFetch<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url);
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

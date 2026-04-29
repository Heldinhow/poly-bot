import { useEffect, useState } from 'react';
import { apiFetch } from '@/lib/api';
import { Bot, ChevronUp, ChevronDown, Minus } from 'lucide-react';

interface AgentMetric {
  agent_name: string;
  total_bets: number;
  wins: number;
  losses: number;
  pending: number;
  total_pnl: number;
  updated_at: string;
}

function healthColor(winRate: number): string {
  if (winRate >= 0.60) return 'text-green';
  if (winRate >= 0.45) return 'text-orange';
  return 'text-red';
}

function formatPnl(pnl: number): string {
  const sign = pnl >= 0 ? '+' : '';
  return `${sign}$${pnl.toFixed(2)}`;
}

export function AgentDashboard() {
  const [metrics, setMetrics] = useState<AgentMetric[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<keyof AgentMetric>('total_bets');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    apiFetch<AgentMetric[]>('/api/agents/metrics')
      .then(setMetrics)
      .catch((e) => setError(e.message))
      .finally(() => setIsLoading(false));
  }, []);

  function handleSort(key: keyof AgentMetric) {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  }

  const sorted = [...metrics].sort((a, b) => {
    const av = a[sortKey] as number | string;
    const bv = b[sortKey] as number | string;
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  function SortIcon({ col }: { col: keyof AgentMetric }) {
    if (sortKey !== col) return <Minus className="h-3 w-3 opacity-30" />;
    return sortDir === 'asc' ? (
      <ChevronUp className="h-3 w-3" />
    ) : (
      <ChevronDown className="h-3 w-3" />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
        <div className="mb-4 flex items-center gap-2">
          <Bot className="h-5 w-5 text-accent-cyan" />
          <h2 className="font-display text-xl tracking-[3px] uppercase">AGENT PERFORMANCE</h2>
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded bg-bg-elevated" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
        <p className="font-mono text-[11px] text-red">Error: {error}</p>
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bot className="h-5 w-5 text-accent-cyan" />
          <h2 className="font-display text-xl tracking-[3px] uppercase">AGENT PERFORMANCE</h2>
        </div>
        <p className="font-mono text-[11px] text-text-muted">No agent metrics yet. Start scanning to generate data.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
      <div className="mb-4 flex items-center gap-2">
        <Bot className="h-5 w-5 text-accent-cyan" />
        <h2 className="font-display text-xl tracking-[3px] uppercase">AGENT PERFORMANCE</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border-subtle text-[10px] uppercase tracking-wider text-text-muted">
              {(['agent_name', 'total_bets', 'wins', 'losses', 'pending', 'total_pnl'] as const).map((col) => (
                <th
                  key={col}
                  className="cursor-pointer px-2 py-2 hover:text-text-primary"
                  onClick={() => handleSort(col)}
                >
                  <span className="flex items-center gap-1">
                    {col === 'agent_name' ? 'Agent' : col.charAt(0).toUpperCase() + col.slice(1)}
                    <SortIcon col={col} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="text-sm">
            {sorted.map((m) => {
              const winRate = m.total_bets > 0 ? m.wins / m.total_bets : 0;
              return (
                <tr
                  key={m.agent_name}
                  className="border-b border-border-subtle/50 hover:bg-surface-hover"
                >
                  <td className="px-2 py-2.5 font-mono text-xs font-medium">{m.agent_name}</td>
                  <td className="px-2 py-2.5 font-mono text-xs">{m.total_bets}</td>
                  <td className="px-2 py-2.5 font-mono text-xs text-green">{m.wins}</td>
                  <td className="px-2 py-2.5 font-mono text-xs text-red">{m.losses}</td>
                  <td className="px-2 py-2.5 font-mono text-xs text-orange">{m.pending}</td>
                  <td className={`px-2 py-2.5 font-mono text-xs font-medium ${healthColor(winRate)}`}>
                    {formatPnl(m.total_pnl)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

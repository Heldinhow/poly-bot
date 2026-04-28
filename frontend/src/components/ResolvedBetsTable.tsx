import { useState } from 'react';
import { useResolvedBets } from '@/hooks/useDashboard';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function truncateQuestion(q: string, max = 45): string {
  if (q.length <= max) return q;
  return q.slice(0, max) + '…';
}

export default function ResolvedBetsTable() {
  const [limit, setLimit] = useState(50);
  const { data: bets, isLoading, error } = useResolvedBets(limit);

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-lg p-4 md:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-xl tracking-[3px] text-text-primary">
          RESOLVED BETS
        </h2>
        <select
          value={limit}
          onChange={(e) => setLimit(Number(e.target.value))}
          className="bg-bg-deep border border-border-subtle rounded px-2 py-1 text-xs font-mono text-text-secondary cursor-pointer outline-none focus:border-border-medium"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[700px]">
          <thead>
            <tr className="border-b border-border-medium">
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                Market
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                Side
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                Entry
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                Stake
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                Payout
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                P&L
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                AI Prob
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted py-3.5 px-3">
                Resolved
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-border-subtle">
                  {Array.from({ length: 8 }).map((_c, j) => (
                    <td key={j} className="py-3.5 px-3">
                      <div className="h-4 bg-white/5 rounded animate-pulse" />
                    </td>
                  ))}
                </tr>
              ))
            ) : error ? (
              <tr>
                <td
                  colSpan={8}
                  className="py-8 text-center text-red font-mono text-xs"
                >
                  Error loading resolved bets:{" "}
                  {error instanceof Error ? error.message : 'Unknown error'}
                </td>
              </tr>
            ) : !bets || bets.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="py-8 text-center text-text-muted italic"
                >
                  No resolved bets yet
                </td>
              </tr>
            ) : (
              bets.map((bet) => {
                const pnl =
                  bet.result === 'win' ? bet.payout - bet.stake : -bet.stake;
                const pnlColor =
                  pnl > 0
                    ? 'text-green'
                    : pnl < 0
                      ? 'text-red'
                      : 'text-text-secondary';
                const pnlSign = pnl >= 0 ? '+' : '-';
                const pnlValue = Math.abs(pnl).toFixed(2);

                return (
                  <tr
                    key={bet.id}
                    className="border-b border-border-subtle hover:bg-white/[0.015] transition-colors"
                  >
                    <td className="py-3.5 px-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="font-mono text-xs text-text-secondary truncate inline-block max-w-[240px]"
                          title={bet.question}
                        >
                          {truncateQuestion(bet.question)}
                        </span>
                        {bet.result === 'win' ? (
                          <span className="px-2 py-[2px] rounded text-[10px] uppercase tracking-[1px] font-semibold bg-green-dim text-green shrink-0">
                            WIN
                          </span>
                        ) : (
                          <span className="px-2 py-[2px] rounded text-[10px] uppercase tracking-[1px] font-semibold bg-red-dim text-red shrink-0">
                            LOSS
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-3">
                      {bet.outcome.toUpperCase() === 'YES' ? (
                        <span className="px-2 py-[2px] rounded text-[10px] uppercase tracking-[1px] font-semibold bg-green-dim text-green">
                          YES
                        </span>
                      ) : (
                        <span className="px-2 py-[2px] rounded text-[10px] uppercase tracking-[1px] font-semibold bg-red-dim text-red">
                          NO
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-xs text-text-secondary">
                      {(bet.price * 100).toFixed(1)}%
                    </td>
                    <td className="py-3.5 px-3 font-mono text-xs text-text-secondary">
                      ${bet.stake.toFixed(2)}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-xs text-text-secondary">
                      ${bet.payout.toFixed(2)}
                    </td>
                    <td
                      className={`py-3.5 px-3 font-mono text-xs font-medium ${pnlColor}`}
                    >
                      {pnlSign}${pnlValue}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-xs text-cyan">
                      {bet.probability_ai != null
                        ? `${(bet.probability_ai * 100).toFixed(1)}%`
                        : 'N/A'}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-xs text-text-muted">
                      {formatDate(bet.resolved_at)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

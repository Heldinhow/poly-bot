import { useOpenBets } from '@/hooks/useDashboard';
import { Loader2 } from 'lucide-react';

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 1) + '\u2026';
}

function SkeletonRow() {
  return (
    <tr className="animate-pulse border-b border-border-subtle">
      {Array.from({ length: 8 }).map((_, i) => (
        <td key={i} className="py-3.5 px-3">
          <div className="h-4 bg-white/5 rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

export default function OpenBetsTable() {
  const { data: bets, isLoading, error } = useOpenBets();

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-lg">
      {/* Panel Header */}
      <div className="px-5 py-4 border-b border-border-subtle">
        <h2 className="font-display text-xl tracking-[3px] text-text-primary">
          ACTIVE POSITIONS
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[700px]">
          <thead>
            <tr className="border-b border-border-medium">
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Market
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Side
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Entry
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Stake
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Payout
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Edge
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                AI Prob
              </th>
              <th className="py-3.5 px-3 text-left font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
                Date
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <>
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
              </>
            ) : error ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-text-muted">
                  <div className="flex items-center justify-center gap-2">
                    <span className="text-red">Error loading positions</span>
                  </div>
                  <p className="text-xs mt-1">
                    {error instanceof Error ? error.message : 'Unknown error'}
                  </p>
                </td>
              </tr>
            ) : !bets || bets.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="py-8 text-center text-text-muted italic"
                >
                  No active positions
                </td>
              </tr>
            ) : (
              bets.map((bet) => (
                <tr
                  key={bet.id}
                  className="border-b border-border-subtle hover:bg-white/[0.015] transition-colors"
                >
                  {/* Market */}
                  <td className="py-3.5 px-3">
                    <div className="flex flex-col gap-1">
                      <span className="font-mono text-xs text-text-secondary leading-snug">
                        {truncate(bet.question, 55)}
                      </span>
                      <span
                        className={`inline-flex self-start px-2 py-[2px] rounded text-[10px] uppercase tracking-[1px] font-medium ${
                          bet.trading_mode === 'live'
                            ? 'bg-green-dim text-green'
                            : 'bg-cyan-dim text-cyan'
                        }`}
                      >
                        {bet.trading_mode}
                      </span>
                    </div>
                  </td>

                  {/* Side */}
                  <td className="py-3.5 px-3">
                    <span
                      className={`inline-block px-2.5 py-[3px] rounded text-[10px] uppercase tracking-[1px] font-medium ${
                        bet.outcome === 'Yes'
                          ? 'bg-green-dim text-green'
                          : 'bg-red-dim text-red'
                      }`}
                    >
                      {bet.outcome}
                    </span>
                  </td>

                  {/* Entry */}
                  <td className="py-3.5 px-3 font-mono text-xs text-text-secondary">
                    {(bet.price * 100).toFixed(1)}%
                  </td>

                  {/* Stake */}
                  <td className="py-3.5 px-3 font-mono text-xs text-text-secondary">
                    ${bet.stake.toFixed(2)}
                  </td>

                  {/* Payout */}
                  <td className="py-3.5 px-3 font-mono text-xs text-text-secondary">
                    ${bet.payout.toFixed(2)}
                  </td>

                  {/* Edge */}
                  <td className="py-3.5 px-3 font-mono text-xs text-amber">
                    +{(bet.edge * 100).toFixed(0)}%
                  </td>

                  {/* AI Prob */}
                  <td className="py-3.5 px-3 font-mono text-xs text-cyan">
                    {bet.probability_ai !== null
                      ? `${(bet.probability_ai * 100).toFixed(1)}%`
                      : 'N/A'}
                  </td>

                  {/* Date */}
                  <td className="py-3.5 px-3 font-mono text-xs text-text-muted">
                    {formatDate(bet.timestamp)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

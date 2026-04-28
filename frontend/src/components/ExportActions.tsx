import { useStats, useOpenBets, useResolvedBets } from '@/hooks/useDashboard';
import { Download } from 'lucide-react';

function escapeCSV(value: unknown): string {
  const str = String(value ?? '');
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function downloadCSV(filename: string, rows: string[][]) {
  const csv = rows.map((row) => row.map(escapeCSV).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function ExportActions() {
  const { data: stats } = useStats();
  const { data: openBets } = useOpenBets();
  const { data: resolvedBets } = useResolvedBets(1000);

  const exportStats = () => {
    if (!stats) return;
    const rows = [
      ['Metric', 'Value'],
      ['Bankroll', `$${stats.bankroll.toFixed(2)}`],
      ['Initial Bankroll', `$${stats.initial_bankroll.toFixed(2)}`],
      ['ROI', `${stats.roi_pct.toFixed(2)}%`],
      ['Total Bets', String(stats.total_bets)],
      ['Open Bets', String(stats.open_bets)],
      ['Wins', String(stats.wins)],
      ['Losses', String(stats.losses)],
      ['Win Rate', `${stats.win_rate.toFixed(1)}%`],
      ['Sharpe Ratio', stats.sharpe_ratio.toFixed(2)],
      ['Max Drawdown', `${stats.max_drawdown.toFixed(1)}%`],
      ['Underdog Hit Rate', `${stats.underdog_hit_rate.toFixed(1)}%`],
    ];
    downloadCSV(`atlas-stats-${new Date().toISOString().slice(0, 10)}.csv`, rows);
  };

  const exportBets = () => {
    const allBets = [...(openBets || []), ...(resolvedBets || [])];
    if (allBets.length === 0) return;
    const rows = [
      ['ID', 'Market', 'Outcome', 'Price', 'Stake', 'Payout', 'Edge', 'AI Prob', 'Timestamp', 'Resolved', 'Result', 'Trading Mode'],
      ...allBets.map((bet) => [
        String(bet.id),
        bet.question,
        bet.outcome,
        String(bet.price),
        String(bet.stake),
        String(bet.payout),
        String(bet.edge),
        bet.probability_ai != null ? String(bet.probability_ai) : '',
        bet.timestamp,
        String(bet.resolved),
        bet.result || '',
        bet.trading_mode,
      ]),
    ];
    downloadCSV(`atlas-bets-${new Date().toISOString().slice(0, 10)}.csv`, rows);
  };

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={exportStats}
        disabled={!stats}
        className="flex items-center gap-2 rounded-md border border-border-subtle bg-bg-surface px-3 py-1.5 text-[11px] font-mono uppercase tracking-[1px] text-text-secondary transition-all hover:border-border-medium hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Download className="h-3.5 w-3.5" />
        Stats CSV
      </button>
      <button
        onClick={exportBets}
        disabled={!openBets && !resolvedBets}
        className="flex items-center gap-2 rounded-md border border-border-subtle bg-bg-surface px-3 py-1.5 text-[11px] font-mono uppercase tracking-[1px] text-text-secondary transition-all hover:border-border-medium hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Download className="h-3.5 w-3.5" />
        Bets CSV
      </button>
    </div>
  );
}

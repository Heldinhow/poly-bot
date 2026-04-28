import { useStats } from '@/hooks/useDashboard';
import { KpiCard } from './KpiCard';
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Zap,
} from 'lucide-react';

function SkeletonCard() {
  return (
    <div className="relative overflow-hidden rounded-lg border border-border-subtle bg-bg-elevated px-5 py-[18px]">
      <div className="mb-2 h-3 w-16 animate-pulse rounded bg-bg-surface" />
      <div className="mb-1 h-8 w-24 animate-pulse rounded bg-bg-surface" />
      <div className="h-3 w-20 animate-pulse rounded bg-bg-surface" />
    </div>
  );
}

export function KpiRow() {
  const { data, isLoading, error } = useStats();

  if (error) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface px-5 py-[18px]">
        <div className="font-mono text-[11px] text-red">
          Error loading stats:{' '}
          {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const {
    bankroll,
    roi_pct,
    realized_pnl,
    total_staked_resolved,
    realized_roi,
    open_bets,
    resolved_bets,
    wins,
    losses,
    win_rate,
    sharpe_ratio,
    max_drawdown,
  } = data;

  const cards = [
    {
      label: 'Bankroll',
      value: `$${bankroll.toFixed(2)}`,
      sub: `ROI: ${roi_pct >= 0 ? '+' : ''}${roi_pct.toFixed(1)}%`,
      color: 'cyan' as const,
      icon: Wallet,
    },
    {
      label: 'Realized P&L',
      value: `${realized_pnl >= 0 ? '+' : ''}$${Math.abs(realized_pnl).toFixed(2)}`,
      sub: `ROI: ${realized_roi >= 0 ? '+' : ''}${realized_roi.toFixed(1)}% (${total_staked_resolved.toFixed(0)} staked)`,
      color: realized_pnl >= 0 ? ('green' as const) : ('red' as const),
      icon: realized_pnl >= 0 ? TrendingUp : TrendingDown,
    },
    {
      label: 'Win Rate',
      value: `${win_rate.toFixed(1)}%`,
      sub: `${wins} wins / ${losses} losses`,
      color: 'orange' as const,
      icon: Target,
    },
    {
      label: 'Active Positions',
      value: `${open_bets}`,
      sub: `${resolved_bets} resolved`,
      color: 'purple' as const,
      icon: Activity,
    },
    {
      label: 'Sharpe Ratio',
      value: `${sharpe_ratio.toFixed(2)}`,
      sub: `Max DD: ${max_drawdown.toFixed(1)}%`,
      color: 'amber' as const,
      icon: Zap,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {cards.map((card, i) => (
        <KpiCard
          key={card.label}
          label={card.label}
          value={card.value}
          subtext={card.sub}
          color={card.color}
          icon={card.icon}
          delay={0.05 * (i + 1)}
        />
      ))}
    </div>
  );
}

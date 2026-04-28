import { useEffect, useMemo, useState } from 'react';
import { useStats } from '@/hooks/useDashboard';

interface Regime {
  name: string;
  icon: string;
  confidence: number;
  active: boolean;
}

function computeRegimes(stats: {
  roi_pct: number;
  win_rate: number;
  max_drawdown: number;
  sharpe_ratio: number;
  total_bets: number;
}): Regime[] {
  const { roi_pct, win_rate, max_drawdown, sharpe_ratio, total_bets } = stats;

  const regimes: Omit<Regime, 'active'>[] = [
    {
      name: 'Recovery',
      icon: '▲',
      confidence: Math.min(100, Math.max(5, roi_pct * 3 + win_rate)),
    },
    {
      name: 'Crisis',
      icon: '▼',
      confidence: Math.min(100, Math.max(5, max_drawdown * 2)),
    },
    {
      name: 'Rate Tightening',
      icon: '◆',
      confidence: Math.min(100, Math.max(5, (50 - win_rate) * 2)),
    },
    {
      name: 'Bull',
      icon: '●',
      confidence: Math.min(100, Math.max(5, roi_pct * 5 + sharpe_ratio * 20)),
    },
    {
      name: 'Euphoria',
      icon: '★',
      confidence: Math.min(100, Math.max(5, roi_pct * 2)),
    },
  ];

  const maxConfidence = Math.max(...regimes.map((r) => r.confidence));
  return regimes.map((r) => ({ ...r, active: r.confidence === maxConfidence }));
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 rounded-md border border-border-subtle bg-bg-deep px-3.5 py-2.5">
      <div className="h-8 w-8 animate-pulse rounded-md bg-bg-elevated" />
      <div className="flex-1">
        <div className="mb-1 h-3 w-20 animate-pulse rounded bg-bg-elevated" />
        <div className="h-2 w-16 animate-pulse rounded bg-bg-elevated" />
      </div>
      <div className="h-1 w-[60px] rounded-full bg-bg-elevated" />
    </div>
  );
}

export function PrismRegime() {
  const { data, isLoading, error } = useStats();
  const [animatedValues, setAnimatedValues] = useState<number[]>([]);

  const regimes = useMemo(() => {
    if (!data) return [];
    return computeRegimes(data);
  }, [data]);

  // Reset animated values whenever regimes change
  useEffect(() => {
    setAnimatedValues(regimes.map(() => 0));
  }, [regimes]);

  // Staggered animation
  useEffect(() => {
    if (regimes.length === 0) return;
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    regimes.forEach((_, i) => {
      timeouts.push(
        setTimeout(() => {
          setAnimatedValues((prev) => {
            const next = [...prev];
            next[i] = regimes[i].confidence;
            return next;
          });
        }, 100 * i)
      );
    });
    return () => timeouts.forEach(clearTimeout);
  }, [regimes]);

  if (error) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
        <h2 className="font-display mb-4 text-xl tracking-[3px] text-text-primary uppercase">
          PRISM REGIME
        </h2>
        <div className="font-mono text-[11px] text-red">
          Error loading regime data:{' '}
          {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
        <h2 className="font-display mb-4 text-xl tracking-[3px] text-text-primary uppercase">
          PRISM REGIME
        </h2>
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      </div>
    );
  }

  const iconColors: Record<string, string> = {
    Recovery: 'bg-green-dim text-green',
    Crisis: 'bg-red-dim text-red',
    'Rate Tightening': 'bg-orange-dim text-orange',
    Bull: 'bg-cyan-dim text-cyan',
    Euphoria: 'bg-purple-dim text-purple',
  };

  const barColors: Record<string, string> = {
    Recovery: 'bg-green',
    Crisis: 'bg-red',
    'Rate Tightening': 'bg-orange',
    Bull: 'bg-cyan',
    Euphoria: 'bg-purple',
  };

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
      <h2 className="font-display mb-4 text-xl tracking-[3px] text-text-primary uppercase">
        PRISM REGIME
      </h2>
      <div className="flex flex-col gap-2">
        {regimes.map((regime, i) => (
          <div
            key={regime.name}
            className={`flex items-center gap-3 rounded-md border border-border-subtle bg-bg-deep px-3.5 py-2.5 ${
              regime.active ? 'border-green/20 bg-green/[0.03]' : ''
            }`}
          >
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-md text-sm ${iconColors[regime.name]}`}
            >
              {regime.icon}
            </div>
            <div className="min-w-0 flex-1">
              <div className="font-mono text-xs font-medium tracking-[0.5px] text-text-primary">
                {regime.name}
              </div>
            </div>
            <div className="mr-2 font-mono text-[11px] text-text-muted">
              {Math.round(regime.confidence)}%
            </div>
            <div className="h-1 w-[60px] overflow-hidden rounded-full bg-bg-elevated">
              <div
                className={`h-full rounded-full ${barColors[regime.name]} transition-all duration-1000`}
                style={{ width: `${animatedValues[i] ?? 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

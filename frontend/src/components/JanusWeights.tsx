import { useStats } from '@/hooks/useDashboard';

interface Agent {
  initials: string;
  name: string;
  role: string;
  weight: number; // 0-1
  accuracy: number; // 0-100
  trades: number;
  color: 'cyan' | 'orange' | 'green' | 'purple';
}

const STATIC_AGENTS: Omit<Agent, 'accuracy' | 'trades'>[] = [
  {
    initials: 'DR',
    name: 'DRUCKENMILLER',
    role: 'Momentum · Macro',
    weight: 0.35,
    color: 'cyan',
  },
  {
    initials: 'AS',
    name: 'ASCHENBRENNER',
    role: 'Contrarian · Risk',
    weight: 0.35,
    color: 'orange',
  },
  {
    initials: 'AC',
    name: 'ACKMAN',
    role: 'Value · Catalyst',
    weight: 0.30,
    color: 'green',
  },
];

const avatarClassMap: Record<Agent['color'], string> = {
  cyan: 'bg-cyan-dim text-cyan border-cyan/20',
  orange: 'bg-orange-dim text-orange border-orange/20',
  green: 'bg-green-dim text-green border-green/20',
  purple: 'bg-purple-dim text-purple border-purple/20',
};

const weightColorMap: Record<Agent['color'], string> = {
  cyan: 'text-cyan',
  orange: 'text-orange',
  green: 'text-green',
  purple: 'text-purple',
};

function SkeletonCard() {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface p-5 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 animate-pulse items-center justify-center rounded-full bg-bg-elevated" />
      <div className="mx-auto mb-0.5 h-4 w-28 animate-pulse rounded bg-bg-elevated" />
      <div className="mx-auto mb-4 h-3 w-20 animate-pulse rounded bg-bg-elevated" />
      <div className="space-y-1">
        <div className="h-5 animate-pulse rounded bg-bg-elevated" />
        <div className="h-5 animate-pulse rounded bg-bg-elevated" />
        <div className="h-5 animate-pulse rounded bg-bg-elevated" />
      </div>
    </div>
  );
}

export default function JanusWeights() {
  const { data, isLoading, error } = useStats();

  const agents: Agent[] = STATIC_AGENTS.map((agent) => ({
    ...agent,
    accuracy: data ? Math.round(data.win_rate * 10) / 10 : 65,
    trades: data ? data.resolved_bets : 0,
  }));

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface p-6">
      {/* Header */}
      <div className="mb-5">
        <h2 className="font-display text-xl tracking-[3px] text-text-primary uppercase">
          JANUS · SUPERINVESTOR COHORT
        </h2>
        <p className="mt-1 font-mono text-[11px] tracking-[0.5px] text-text-muted">
          AI Agent Weight Distribution
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-red/20 bg-red-dim px-4 py-3">
          <p className="font-mono text-[11px] text-red">
            Error loading stats:{' '}
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* Cards */}
      {!isLoading && !error && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {agents.map((agent, i) => (
            <div
              key={agent.initials}
              className="rounded-lg border border-border-subtle bg-bg-surface p-5 text-center transition-all duration-200 hover:-translate-y-0.5 hover:border-border-medium animate-fade-up"
              style={{ animationDelay: `${0.1 * (i + 1)}s` }}
            >
              {/* Avatar */}
              <div
                className={`mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full border font-display text-lg tracking-[1px] ${avatarClassMap[agent.color]}`}
              >
                {agent.initials}
              </div>

              {/* Name */}
              <div className="font-display text-base tracking-[2px] text-text-primary mb-0.5">
                {agent.name}
              </div>

              {/* Role */}
              <div className="font-mono text-[10px] uppercase tracking-[1px] text-text-muted mb-4">
                {agent.role}
              </div>

              {/* Stats */}
              <div className="space-y-0">
                <div className="flex items-center justify-between border-t border-border-subtle py-1.5">
                  <span className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-muted">
                    Weight
                  </span>
                  <span className={`font-mono text-xs font-medium ${weightColorMap[agent.color]}`}>
                    {agent.weight.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between border-t border-border-subtle py-1.5">
                  <span className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-muted">
                    Accuracy
                  </span>
                  <span className="font-mono text-xs font-medium text-green">
                    {agent.accuracy.toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between border-t border-border-subtle py-1.5">
                  <span className="font-mono text-[10px] uppercase tracking-[0.5px] text-text-muted">
                    Trades
                  </span>
                  <span className="font-mono text-xs font-medium text-text-primary">
                    {agent.trades}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

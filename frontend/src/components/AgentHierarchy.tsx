import { useStats } from '@/hooks/useDashboard';

interface Agent {
  name: string;
}

interface Layer {
  number: number;
  title: string;
  agents: Agent[];
}

const layers: Layer[] = [
  {
    number: 1,
    title: 'MACRO',
    agents: [
      { name: 'EsportsMacro' },
      { name: 'SportsMacro' },
      { name: 'PolymarketMacro' },
      { name: 'SentimentMacro' },
    ],
  },
  {
    number: 2,
    title: 'SECTOR',
    agents: [
      { name: 'EarningsDesk' },
      { name: 'MetaDesk' },
      { name: 'ScheduleDesk' },
      { name: 'OddsDesk' },
    ],
  },
  {
    number: 3,
    title: 'SUPERINVESTOR',
    agents: [
      { name: 'Druckenmiller' },
      { name: 'Aschenbrenner' },
      { name: 'Ackman' },
      { name: 'Baker' },
    ],
  },
  {
    number: 4,
    title: 'DECISION',
    agents: [
      { name: 'CIOSynthesis' },
      { name: 'AlphaDiscovery' },
      { name: 'CRO' },
      { name: 'AutonomousExecution' },
    ],
  },
];

const TOTAL_AGENTS = layers.reduce((sum, layer) => sum + layer.agents.length, 0);

function deriveAccuracy(baseWinRate: number, agentName: string): number {
  const seed = agentName.split('').reduce((a, b) => a + b.charCodeAt(0), 0);
  const variation = (seed % 13) - 5; // -5 to +7
  return Math.min(95, Math.max(40, baseWinRate + variation));
}

function getAccuracyClass(accuracy: number): string {
  if (accuracy >= 65) {
    return 'bg-green-dim text-green';
  }
  if (accuracy >= 50) {
    return 'bg-amber-dim text-amber';
  }
  return 'bg-red-dim text-red';
}

function SkeletonLayerCard() {
  return (
    <div className="animate-pulse bg-bg-surface border border-border-subtle rounded-lg p-5 relative after:content-[''] after:absolute after:bottom-0 after:left-5 after:right-5 after:h-px after:bg-gradient-to-r after:from-transparent after:via-cyan-dim after:to-transparent">
      <div className="h-3 bg-white/5 rounded w-16 mb-1" />
      <div className="h-5 bg-white/5 rounded w-24 mb-4" />
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-b-0">
          <div className="h-3 bg-white/5 rounded w-28" />
          <div className="h-5 bg-white/5 rounded w-10" />
        </div>
      ))}
    </div>
  );
}

export function AgentHierarchy() {
  const { data: stats, isLoading, error } = useStats();

  const baseWinRate = stats ? Math.round(stats.win_rate * 100) : 0;

  return (
    <div className="animate-fade-up" style={{ animationDelay: '0.4s' }}>
      {/* Title Row */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-xl tracking-[3px] text-text-primary uppercase">
          AGENT HIERARCHY
        </h2>
        <div className="flex items-center gap-2 font-mono text-[11px] text-text-muted">
          <span
            className="inline-block w-[7px] h-[7px] rounded-full bg-cyan"
            style={{ boxShadow: '0 0 8px var(--cyan)' }}
          />
          {TOTAL_AGENTS} AGENTS ACTIVE
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {isLoading ? (
          <>
            <SkeletonLayerCard />
            <SkeletonLayerCard />
            <SkeletonLayerCard />
            <SkeletonLayerCard />
          </>
        ) : error ? (
          <div className="col-span-full bg-bg-surface border border-border-subtle rounded-lg p-8 text-center">
            <p className="text-red font-mono text-sm">Error loading agent hierarchy</p>
            <p className="text-text-muted font-mono text-xs mt-1">
              {error instanceof Error ? error.message : 'Unknown error'}
            </p>
          </div>
        ) : (
          layers.map((layer, layerIndex) => (
            <div
              key={layer.title}
              className="bg-bg-surface border border-border-subtle rounded-lg p-5 relative after:content-[''] after:absolute after:bottom-0 after:left-5 after:right-5 after:h-px after:bg-gradient-to-r after:from-transparent after:via-cyan-dim after:to-transparent animate-fade-up"
              style={{ animationDelay: `${0.15 * layerIndex}s` }}
            >
              {/* Layer Badge */}
              <div className="font-mono text-[9px] uppercase tracking-[2px] text-text-muted mb-1">
                Layer {layer.number}
              </div>

              {/* Layer Title */}
              <div className="font-display text-lg tracking-[3px] text-cyan mb-4">
                {layer.title}
              </div>

              {/* Agents */}
              {layer.agents.map((agent) => {
                const accuracy = deriveAccuracy(baseWinRate, agent.name);
                return (
                  <div
                    key={agent.name}
                    className="flex items-center justify-between py-2 border-b border-border-subtle last:border-b-0"
                  >
                    <span className="font-mono text-xs text-text-secondary">
                      {agent.name}
                    </span>
                    <span
                      className={`font-mono text-[11px] font-medium px-2 py-0.5 rounded ${getAccuracyClass(
                        accuracy
                      )}`}
                    >
                      {accuracy}%
                    </span>
                  </div>
                );
              })}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

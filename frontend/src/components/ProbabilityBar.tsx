interface Props {
  aiProbability: number;
  marketProbability: number;
  edge: number;
}

export default function ProbabilityBar({ aiProbability, marketProbability, edge }: Props) {
  const aiPct = Math.round(aiProbability * 100);
  const marketPct = Math.round(marketProbability * 100);
  const edgeLabel = edge >= 0 ? `+${edge.toFixed(1)}%` : `${edge.toFixed(1)}%`;

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 text-xs">
        <span className="text-accent-cyan font-medium">AI {aiPct}%</span>
        <span className="text-text-muted">vs Market {marketPct}%</span>
        <span className={`ml-auto font-mono ${edge >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
          Edge {edgeLabel}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-surface-hover overflow-hidden flex">
        <div className="h-full bg-accent-cyan rounded-l-full" style={{ width: `${aiPct}%` }} />
        <div className="h-full bg-surface-hover" style={{ width: `${Math.max(0, marketPct - aiPct)}%` }} />
      </div>
    </div>
  );
}

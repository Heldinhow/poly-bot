interface Props {
  decision: string;
}

export default function DecisionBadge({ decision }: Props) {
  const config = {
    ACCEPT: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
    REJECT: 'bg-rose-500/20 text-rose-400 border border-rose-500/30',
    SKIP: 'bg-text-muted/20 text-text-muted border border-text-muted/30',
  }[decision] ?? 'bg-text-muted/20 text-text-muted border border-text-muted/30';

  return (
    <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${config}`}>
      {decision}
    </span>
  );
}

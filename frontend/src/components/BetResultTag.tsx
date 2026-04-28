interface Props {
  outcome: string | null;
  stake: number | null;
}

export default function BetResultTag({ outcome, stake }: Props) {
  if (!outcome) {
    return (
      <span className="rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-medium text-amber-400 border border-amber-500/30">
        PENDING
      </span>
    );
  }

  if (outcome === 'WIN') {
    return (
      <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/30">
        WIN {stake ? `+$${stake.toFixed(2)}` : ''}
      </span>
    );
  }

  if (outcome === 'LOSS') {
    return (
      <span className="rounded-full bg-rose-500/20 px-2.5 py-0.5 text-xs font-medium text-rose-400 border border-rose-500/30">
        LOSS {stake ? `-$${stake.toFixed(2)}` : ''}
      </span>
    );
  }

  return null;
}

import { AuditMarket } from '@/lib/api';

interface Props {
  items: AuditMarket[];
}

function StatPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className={`rounded-lg border px-4 py-2 ${color}`}>
      <span className="text-xs font-medium uppercase tracking-wider text-text-muted">{label}</span>
      <p className="text-lg font-mono font-bold text-text-primary">{value}</p>
    </div>
  );
}

export default function AuditStatsRow({ items }: Props) {
  const acceptCount = items.filter(i => i.decision === 'ACCEPT').length;
  const rejectCount = items.filter(i => i.decision === 'REJECT').length;
  const skipCount = items.filter(i => i.decision === 'SKIP').length;
  const acceptedWithOutcome = items.filter(i => i.decision === 'ACCEPT' && i.outcome);
  const wins = acceptedWithOutcome.filter(i => i.outcome === 'WIN').length;
  const losses = acceptedWithOutcome.filter(i => i.outcome === 'LOSS').length;

  return (
    <div className="flex flex-wrap gap-3">
      <StatPill label="ACCEPT" value={String(acceptCount)} color="bg-emerald-500/10 border-emerald-500/20 text-emerald-400" />
      <StatPill label="REJECT" value={String(rejectCount)} color="bg-rose-500/10 border-rose-500/20 text-rose-400" />
      <StatPill label="SKIP" value={String(skipCount)} color="bg-text-muted/10 border-text-muted/20 text-text-muted" />
      <StatPill label="W/L" value={`${wins}W / ${losses}L`} color="bg-amber-500/10 border-amber-500/20 text-amber-400" />
    </div>
  );
}

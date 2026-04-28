import type { LucideIcon } from 'lucide-react';

export interface KpiCardProps {
  label: string;
  value: string;
  subtext: string;
  color: 'cyan' | 'green' | 'orange' | 'purple' | 'amber' | 'red';
  icon: LucideIcon;
  delay?: number;
}

const textColorMap: Record<KpiCardProps['color'], string> = {
  cyan: 'text-cyan',
  green: 'text-green',
  orange: 'text-orange',
  purple: 'text-purple',
  amber: 'text-amber',
  red: 'text-red',
};

const bgColorMap: Record<KpiCardProps['color'], string> = {
  cyan: 'bg-cyan',
  green: 'bg-green',
  orange: 'bg-orange',
  purple: 'bg-purple',
  amber: 'bg-amber',
  red: 'bg-red',
};

export function KpiCard({ label, value, subtext, color, icon: Icon, delay = 0 }: KpiCardProps) {
  return (
    <div
      className="relative overflow-hidden rounded-lg border border-border-subtle bg-bg-surface px-5 py-[18px] animate-fade-up"
      style={{ animationDelay: `${delay}s` }}
    >
      <div className={`absolute left-0 right-0 top-0 h-0.5 ${bgColorMap[color]}`} />
      <div className="mb-2 flex items-center gap-2">
        <Icon size={14} className="text-text-muted" />
        <span className="font-mono text-[10px] uppercase tracking-[1.5px] text-text-muted">
          {label}
        </span>
      </div>
      <div className={`font-display text-[32px] tracking-[2px] ${textColorMap[color]}`}>
        {value}
      </div>
      <div className="mt-1 font-mono text-[11px] text-text-secondary">{subtext}</div>
    </div>
  );
}

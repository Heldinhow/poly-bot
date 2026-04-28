import { useState, useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useTimeseries } from '@/hooks/useDashboard';

type TimeRange = 7 | 30 | 90 | 'ALL';

const TABS: { label: string; value: TimeRange }[] = [
  { label: '7D', value: 7 },
  { label: '30D', value: 30 },
  { label: '90D', value: 90 },
  { label: 'ALL', value: 'ALL' },
];

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor(
    (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (diffDays < 7) {
    return date.toLocaleDateString('en-US', { weekday: 'short' });
  }
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatBankroll(value: number): string {
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}k`;
  }
  return `$${value.toFixed(0)}`;
}

interface TimeseriesPoint {
  date: string;
  realized_pnl: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: TimeseriesPoint & { formattedDate: string };
  }>;
  label?: string;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const point = payload[0].payload;
  const date = new Date(point.date);
  const dateStr = date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  const isProfit = point.realized_pnl >= 0;
  const color = isProfit ? '#00e5ff' : '#ff4d6d';

  return (
    <div className="rounded-lg border border-border-medium bg-bg-card px-4 py-3 shadow-lg">
      <p className="mb-1 text-xs uppercase tracking-wider text-text-muted font-mono">
        {dateStr}
      </p>
      <p className="text-sm font-mono" style={{ color }}>
        ${point.realized_pnl >= 0 ? '+' : ''}
        {point.realized_pnl.toLocaleString('en-US', { maximumFractionDigits: 2 })}
      </p>
    </div>
  );
}

type ViewMode = 'realized' | 'equity';

export default function PerformanceChart() {
  const [activeTab, setActiveTab] = useState<TimeRange>(30);
  const [viewMode, setViewMode] = useState<ViewMode>('realized');
  const daysParam = activeTab === 'ALL' ? undefined : activeTab;
  const { data, isLoading, error } = useTimeseries(daysParam);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.map((point) => ({
      ...point,
      formattedDate: formatDate(point.date),
    }));
  }, [data]);

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-surface">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-3">
          <h2 className="font-display text-xl tracking-[3px] text-text-primary uppercase">
            Portfolio Performance
          </h2>
          {/* Toggle: Realized vs Equity */}
          <div className="rounded-md bg-bg-deep p-[3px] flex gap-[2px]">
            <button
              onClick={() => setViewMode('realized')}
              className={`rounded-sm px-3 py-1 text-xs font-mono transition-colors ${
                viewMode === 'realized'
                  ? 'bg-bg-elevated text-cyan'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              Realized P&L
            </button>
            <button
              onClick={() => setViewMode('equity')}
              className={`rounded-sm px-3 py-1 text-xs font-mono transition-colors ${
                viewMode === 'equity'
                  ? 'bg-bg-elevated text-cyan'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              Equity
            </button>
          </div>
        </div>
        <div className="rounded-md bg-bg-deep p-[3px]">
          <div className="flex gap-[2px]">
            {TABS.map((tab) => (
              <button
                key={tab.label}
                onClick={() => setActiveTab(tab.value)}
                className={`rounded-sm px-3 py-1 text-xs font-mono transition-colors ${
                  activeTab === tab.value
                    ? 'bg-bg-elevated text-cyan'
                    : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart Area */}
      <div className="px-5 pb-5">
        {isLoading && (
          <div className="flex h-[280px] animate-pulse flex-col gap-3">
            <div className="h-4 w-1/3 rounded bg-bg-elevated" />
            <div className="flex-1 rounded bg-bg-deep" />
          </div>
        )}

        {error && !isLoading && (
          <div className="flex h-[280px] items-center justify-center">
            <p className="text-sm text-text-muted">
              Unable to load chart data
            </p>
          </div>
        )}

        {!isLoading && !error && chartData.length === 0 && (
          <div className="flex h-[280px] items-center justify-center">
            <p className="text-sm text-text-muted">No data available</p>
          </div>
        )}

        {!isLoading && !error && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart
              data={chartData}
              margin={{ top: 5, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="bankrollGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="rgba(0,229,255,0.12)" />
                  <stop offset="100%" stopColor="rgba(0,229,255,0)" />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="0"
                horizontal={true}
                vertical={false}
                stroke="rgba(255,255,255,0.03)"
              />
              <XAxis
                dataKey="formattedDate"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#55556a', fontSize: 11, fontFamily: 'DM Mono, monospace' }}
                dy={8}
              />
              <YAxis
                orientation="right"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#55556a', fontSize: 11, fontFamily: 'DM Mono, monospace' }}
                tickFormatter={formatBankroll}
                dx={4}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
              <Area
                type="monotone"
                dataKey="realized_pnl"
                stroke="#00e5ff"
                strokeWidth={2}
                fill="url(#bankrollGradient)"
                activeDot={{
                  r: 5,
                  fill: '#00e5ff',
                  stroke: '#06060c',
                  strokeWidth: 2,
                }}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

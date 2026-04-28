import { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';
import { useAuditSummary } from '@/hooks/useAudit';
import ExecutionFeed from '@/components/ExecutionFeed';
import AuditFilterBar from '@/components/AuditFilterBar';
import AuditStatsRow from '@/components/AuditStatsRow';
import MarketCard from '@/components/MarketCard';

export default function AuditPage() {
  const [expandedMarket, setExpandedMarket] = useState<string | null>(null);
  const [params, setParams] = useState(() => {
    const p = new URLSearchParams(window.location.search);
    return {
      decision: p.get('decision') || undefined,
      since: p.get('since') || undefined,
      bet_result: p.get('bet_result') || undefined,
    };
  });

  useEffect(() => {
    const onChange = () => {
      const p = new URLSearchParams(window.location.search);
      setParams({
        decision: p.get('decision') || undefined,
        since: p.get('since') || undefined,
        bet_result: p.get('bet_result') || undefined,
      });
    };
    window.addEventListener('popstate', onChange);
    return () => window.removeEventListener('popstate', onChange);
  }, []);

  const { data, isLoading, error } = useAuditSummary(params);

  if (error) {
    return (
      <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-rose-400">
        Unable to reach audit API — retrying... ({error instanceof Error ? error.message : 'Unknown error'})
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-2 mb-6">
        <ShieldCheck className="h-6 w-6 text-accent-cyan" />
        <h2 className="text-2xl font-bold text-text-primary">Execution Audit</h2>
      </div>

      <ExecutionFeed />

      <AuditFilterBar />

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 animate-pulse rounded-xl bg-surface-elevated border border-border-subtle" />
          ))}
        </div>
      ) : data?.items && data.items.length > 0 ? (
        <>
          <AuditStatsRow items={data.items} />
          <div className="space-y-3">
            {data.items.map(market => (
              <MarketCard
                key={market.market_id}
                market={market}
                expanded={expandedMarket === market.market_id}
                onToggle={() => setExpandedMarket(expandedMarket === market.market_id ? null : market.market_id)}
              />
            ))}
          </div>
          {data.next_cursor && (
            <p className="text-center text-sm text-text-muted py-4">
              End of results — cursor available but pagination UI not yet implemented
            </p>
          )}
        </>
      ) : (
        <div className="text-center py-12 text-text-muted">
          {params.decision || params.since || params.bet_result
            ? 'No markets match your filters'
            : 'No markets audited yet'}
        </div>
      )}
    </div>
  );
}
import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { AuditMarket } from '@/lib/api';
import { useMarketAudit } from '@/hooks/useAudit';
import DecisionBadge from '@/components/DecisionBadge';
import ProbabilityBar from '@/components/ProbabilityBar';
import BetResultTag from '@/components/BetResultTag';
import TruthClaimsAccordion from '@/components/TruthClaimsAccordion';
import ExecutionStepsAccordion from '@/components/ExecutionStepsAccordion';

interface Props {
  market: AuditMarket;
  expanded: boolean;
  onToggle: () => void;
}

export default function MarketCard({ market, expanded, onToggle }: Props) {
  const { data: audit, isLoading } = useMarketAudit(expanded ? market.market_id : null);

  const aiProb = market.probabilities?.[0] ?? (market.yes_price_at_analysis ? 1 - market.yes_price_at_analysis : null);
  const marketProb = market.yes_price_at_analysis ?? null;

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-elevated overflow-hidden">
      <button onClick={onToggle} className="flex w-full items-center justify-between p-4 text-left hover:bg-surface-hover/50 transition-colors">
        <div className="flex items-center gap-3 min-w-0">
          <DecisionBadge decision={market.decision} />
          <div className="min-w-0">
            <p className="text-sm text-text-primary truncate max-w-[400px]">{market.question || market.market_id}</p>
            {aiProb !== null && marketProb !== null && (
              <p className="text-xs text-text-muted mt-0.5">
                AI {(aiProb * 100).toFixed(0)}% vs Market {(marketProb * 100).toFixed(0)}%
                <span className={`ml-2 font-mono ${market.edge >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {market.edge >= 0 ? '+' : ''}{market.edge.toFixed(1)}% edge
                </span>
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0 ml-4">
          {market.decision === 'ACCEPT' && <BetResultTag outcome={market.outcome} stake={market.stake} />}
          {market.execution_count > 1 && <span className="text-xs text-text-muted">{market.execution_count} runs</span>}
          {expanded ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border-subtle px-4 pb-4 pt-3 space-y-4">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">Decision</h4>
            <p className="text-sm text-text-secondary">
              {market.decision === 'ACCEPT'
                ? `ACCEPT — ${market.reject_reason || 'Bet placed'}`
                : market.decision === 'REJECT'
                ? `REJECT — ${market.reject_reason || 'No reason recorded'}`
                : 'SKIP — Not enough confidence'}
            </p>
          </div>

          {aiProb !== null && marketProb !== null && (
            <ProbabilityBar aiProbability={aiProb} marketProbability={marketProb} edge={market.edge} />
          )}

          {isLoading ? (
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <div className="h-4 w-4 border-2 border-accent-cyan/30 border-t-accent-cyan rounded-full animate-spin" />
              Loading audit details...
            </div>
          ) : audit ? (
            <>
              <TruthClaimsAccordion claims={audit.truth_claims} />

              {market.reasoning_summary && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">Reasoning</h4>
                  <p className="text-sm text-text-secondary whitespace-pre-wrap">{market.reasoning_summary}</p>
                </div>
              )}

              {audit.decision_factors?.[0] && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-1">Bet Sizing</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="rounded-lg bg-bg-deep p-2">
                      <p className="text-[10px] uppercase tracking-wider text-text-muted">AI Prob</p>
                      <p className="text-sm font-mono text-text-primary">{(audit.decision_factors[0].ai_probability * 100).toFixed(1)}%</p>
                    </div>
                    <div className="rounded-lg bg-bg-deep p-2">
                      <p className="text-[10px] uppercase tracking-wider text-text-muted">Implied</p>
                      <p className="text-sm font-mono text-text-primary">{(audit.decision_factors[0].implied_probability * 100).toFixed(1)}%</p>
                    </div>
                    <div className="rounded-lg bg-bg-deep p-2">
                      <p className="text-[10px] uppercase tracking-wider text-text-muted">Stake</p>
                      <p className="text-sm font-mono text-text-primary">{audit.decision_factors[0].stake ? `$${audit.decision_factors[0].stake.toFixed(2)}` : '—'}</p>
                    </div>
                    <div className="rounded-lg bg-bg-deep p-2">
                      <p className="text-[10px] uppercase tracking-wider text-text-muted">Kelly</p>
                      <p className="text-sm font-mono text-text-primary">{audit.decision_factors[0].kelly_fraction ? `${(audit.decision_factors[0].kelly_fraction * 100).toFixed(0)}%` : '—'}</p>
                    </div>
                  </div>
                </div>
              )}

              {market.first_execution_id && (
                <ExecutionStepsAccordion
                  executions={[{ id: market.first_execution_id, status: '' }]}
                  defaultExecutionId={market.first_execution_id}
                />
              )}
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
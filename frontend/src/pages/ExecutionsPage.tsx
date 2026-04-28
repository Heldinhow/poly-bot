import { useState } from 'react';
import { useExecutions, useExecutionSteps } from '@/hooks/useExecutions';
import { Activity, ChevronDown, ChevronUp, Clock, Terminal } from 'lucide-react';

export default function ExecutionsPage() {
  const { executions, isLoading } = useExecutions();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isLoading) return <div className="p-8 text-text-muted">Loading executions...</div>;

  const statusColors: Record<string, string> = {
    queued: 'bg-text-muted/20 text-text-muted',
    claimed: 'bg-accent-cyan/20 text-accent-cyan',
    running: 'bg-amber-500/20 text-amber-400',
    completed: 'bg-emerald-500/20 text-emerald-400',
    failed: 'bg-rose-500/20 text-rose-400',
    cancelled: 'bg-text-muted/20 text-text-muted',
  };

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2">
        <Activity className="h-6 w-6 text-accent-cyan" />
        <h2 className="text-2xl font-bold text-text-primary">Executions</h2>
      </div>

      <div className="space-y-3">
        {executions?.map(exec => (
          <div key={exec.id} className="rounded-xl border border-border-subtle bg-surface-elevated">
            <button
              onClick={() => setExpandedId(expandedId === exec.id ? null : exec.id)}
              className="flex w-full items-center justify-between p-4 text-left"
            >
              <div className="flex items-center gap-4">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[exec.status] || 'bg-text-muted/20 text-text-muted'}`}>
                  {exec.status}
                </span>
                <div>
                  <p className="text-sm font-medium text-text-primary truncate max-w-[400px]">{exec.market_id}</p>
                  <p className="text-xs text-text-muted">{exec.runtime} {exec.model && `· ${exec.model}`}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {exec.probability !== null && (
                  <span className="text-sm font-mono text-text-secondary">
                    P={exec.probability.toFixed(2)} C={exec.confidence?.toFixed(2) || '?'}
                  </span>
                )}
                {exec.duration_ms && (
                  <span className="flex items-center gap-1 text-xs text-text-muted">
                    <Clock className="h-3 w-3" />
                    {(exec.duration_ms / 1000).toFixed(1)}s
                  </span>
                )}
                {expandedId === exec.id ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
              </div>
            </button>

            {expandedId === exec.id && <ExecutionDetail logId={exec.id} />}
          </div>
        ))}
      </div>
    </div>
  );
}

function ExecutionDetail({ logId }: { logId: string }) {
  const { steps, isLoading } = useExecutionSteps(logId);

  if (isLoading) return <div className="px-4 pb-4 text-sm text-text-muted">Loading steps...</div>;

  const typeIcons: Record<string, string> = {
    text: '📝',
    thinking: '💭',
    tool_use: '🔧',
    tool_result: '✅',
    error: '❌',
    status: '📡',
    log: '📋',
  };

  return (
    <div className="border-t border-border-subtle px-4 pb-4 pt-3">
      <h4 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
        <Terminal className="h-3 w-3" />
        Execution Steps
      </h4>
      <div className="space-y-2 max-h-96 overflow-auto">
        {steps?.map(step => (
          <div key={step.id} className="rounded-lg bg-bg-deep p-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-xs">{typeIcons[step.step_type] || '•'}</span>
              <span className="text-xs font-mono uppercase text-text-muted">{step.step_type}</span>
              <span className="text-xs text-text-muted/50">#{step.seq}</span>
            </div>
            {step.content && <p className="mt-1 text-text-secondary whitespace-pre-wrap">{step.content}</p>}
            {step.tool_name && (
              <p className="mt-1 text-xs text-text-muted">
                Tool: <span className="text-accent-cyan">{step.tool_name}</span>
              </p>
            )}
            {step.tool_output && (
              <pre className="mt-1 max-h-32 overflow-auto rounded bg-surface-elevated p-2 text-xs text-text-secondary font-mono">{step.tool_output}</pre>
            )}
          </div>
        ))}
        {(!steps || steps.length === 0) && (
          <p className="text-sm text-text-muted">No steps recorded yet.</p>
        )}
      </div>
    </div>
  );
}

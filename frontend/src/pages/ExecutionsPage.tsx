import { useState } from 'react';
import { useExecutions, useExecutionSteps } from '@/hooks/useExecutions';
import { Activity, ChevronDown, ChevronUp, Clock, Terminal, Bot, FileText, Cpu } from 'lucide-react';

const statusColors: Record<string, string> = {
  queued: 'bg-text-muted/20 text-text-muted',
  claimed: 'bg-accent-cyan/20 text-accent-cyan',
  running: 'bg-amber-500/20 text-amber-400',
  completed: 'bg-emerald-500/20 text-emerald-400',
  failed: 'bg-rose-500/20 text-rose-400',
  cancelled: 'bg-text-muted/20 text-text-muted',
};

const stepIcons: Record<string, string> = {
  text: '📝',
  thinking: '💭',
  tool_use: '🔧',
  tool_result: '✅',
  error: '❌',
  status: '📡',
  log: '📋',
};

function formatTokens(n: number): string {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k';
  return String(n);
}

function ExecutionCard({ exec }: { exec: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false);
  const { steps, isLoading } = useExecutionSteps(expanded ? (exec.id as string) : '');

  const prob = exec.probability as number | null;
  const conf = exec.confidence as number | null;
  const dur = exec.duration_ms as number | null;
  const tokensIn = exec.input_tokens as number || 0;
  const tokensOut = exec.output_tokens as number || 0;

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-elevated overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-surface-hover/50 transition-colors"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[exec.status as string] || 'bg-text-muted/20 text-text-muted'}`}>
            {exec.status}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {exec.agent_name && (
                <span className="text-xs font-medium text-accent-cyan truncate max-w-[120px]">
                  {exec.agent_name as string}
                </span>
              )}
              <span className="text-xs text-text-muted">{exec.runtime as string}{exec.model ? ` · ${exec.model}` : ''}</span>
            </div>
            <p className="text-sm text-text-primary truncate max-w-[400px] mt-0.5">{exec.market_id as string}</p>
          </div>
        </div>

        <div className="flex items-center gap-4 shrink-0 ml-4">
          {tokensIn > 0 && (
            <span className="hidden sm:flex items-center gap-1 text-xs text-text-muted">
              <Cpu className="h-3 w-3" />
              {formatTokens(tokensIn)} in / {formatTokens(tokensOut)} out
            </span>
          )}
          {dur && (
            <span className="flex items-center gap-1 text-xs text-text-muted">
              <Clock className="h-3 w-3" />
              {(dur / 1000).toFixed(1)}s
            </span>
          )}
          {prob !== null && (
            <span className="text-sm font-mono text-text-secondary">
              P={prob.toFixed(2)} C={conf?.toFixed(2) || '?'}
            </span>
          )}
          {expanded ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-border-subtle px-4 pb-4 pt-3 space-y-4">
          {/* Reasoning */}
          {exec.reasoning && (
            <div>
              <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
                <FileText className="h-3 w-3" />
                Reasoning
              </h4>
              <p className="rounded-lg bg-bg-deep p-3 text-sm text-text-secondary whitespace-pre-wrap">
                {exec.reasoning as string}
              </p>
            </div>
          )}

          {/* Prompt */}
          {exec.prompt_used && (
            <div>
              <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
                <Bot className="h-3 w-3" />
                Prompt ({String(exec.prompt_used).length} chars)
              </h4>
              <pre className="max-h-48 overflow-auto rounded-lg bg-bg-deep p-3 text-xs text-text-secondary font-mono whitespace-pre-wrap">
                {exec.prompt_used as string}
              </pre>
            </div>
          )}

          {/* Results summary */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg bg-bg-deep p-2.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Probability</p>
              <p className="mt-0.5 text-sm font-mono text-text-primary">{prob !== null ? `${(prob * 100).toFixed(1)}%` : '—'}</p>
            </div>
            <div className="rounded-lg bg-bg-deep p-2.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Confidence</p>
              <p className="mt-0.5 text-sm font-mono text-text-primary">{conf !== null ? `${(conf * 100).toFixed(1)}%` : '—'}</p>
            </div>
            <div className="rounded-lg bg-bg-deep p-2.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Tokens</p>
              <p className="mt-0.5 text-sm font-mono text-text-primary">{formatTokens(tokensIn)} in / {formatTokens(tokensOut)} out</p>
            </div>
            <div className="rounded-lg bg-bg-deep p-2.5">
              <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Duration</p>
              <p className="mt-0.5 text-sm font-mono text-text-primary">{dur ? `${(dur / 1000).toFixed(1)}s` : '—'}</p>
            </div>
          </div>

          {/* Execution Steps */}
          <div>
            <h4 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
              <Terminal className="h-3 w-3" />
              Execution Steps
            </h4>
            {isLoading ? (
              <p className="text-sm text-text-muted">Loading steps...</p>
            ) : steps && steps.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-auto">
                {steps.map(step => (
                  <div key={step.id} className="rounded-lg bg-bg-deep p-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-xs">{stepIcons[step.step_type] || '•'}</span>
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
              </div>
            ) : (
              <p className="text-sm text-text-muted">No steps recorded yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ExecutionsPage() {
  const { executions, isLoading } = useExecutions();

  if (isLoading) return <div className="p-8 text-text-muted">Loading executions...</div>;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center gap-2">
        <Activity className="h-6 w-6 text-accent-cyan" />
        <h2 className="text-2xl font-bold text-text-primary">Executions</h2>
        {executions && (
          <span className="ml-2 text-sm text-text-muted">({executions.length})</span>
        )}
      </div>

      <div className="space-y-3">
        {executions?.map(exec => (
          <ExecutionCard key={exec.id} exec={exec} />
        ))}
        {(!executions || executions.length === 0) && (
          <p className="text-sm text-text-muted">No executions yet.</p>
        )}
      </div>
    </div>
  );
}

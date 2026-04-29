import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Clock, Loader2 } from 'lucide-react';
import { useExecutionStream } from '@/hooks/useExecutionStream';
import type { Execution } from '@/hooks/useExecutions';
import TimelineProgressBar from '@/components/TimelineProgressBar';
import ExecutionTimeline from '@/components/ExecutionTimeline';
import ExecutionSummary from '@/components/ExecutionSummary';

const statusColors: Record<string, string> = {
  queued: 'bg-text-muted/20 text-text-muted',
  claimed: 'bg-accent-cyan/20 text-accent-cyan',
  running: 'bg-amber-500/20 text-amber-400',
  completed: 'bg-emerald-500/20 text-emerald-400',
  failed: 'bg-rose-500/20 text-rose-400',
  cancelled: 'bg-text-muted/20 text-text-muted',
};

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}m ${sec}s`;
}

interface Props {
  exec: Execution;
}

export default function LiveExecutionCard({ exec }: Props) {
  const [expanded, setExpanded] = useState(false);
  const isRunning = exec.status === 'running';
  const isCompleted = exec.status === 'completed' || exec.status === 'failed';

  const { steps, isConnected } = useExecutionStream(isRunning || isCompleted ? exec.id : null);

  const [elapsed, setElapsed] = useState(exec.duration_ms || 0);
  useEffect(() => {
    if (!isRunning || !exec.started_at) return;
    const start = new Date(exec.started_at!).getTime();
    const interval = setInterval(() => {
      setElapsed(Date.now() - start);
    }, 1000);
    return () => clearInterval(interval);
  }, [isRunning, exec.started_at]);

  const toolCount = steps.filter(s => s.step_type === 'tool_use').length;

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-elevated overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`flex w-full items-center justify-between p-4 text-left transition-colors ${
          isRunning ? 'bg-amber-500/5 hover:bg-amber-500/10' : 'hover:bg-surface-hover/50'
        }`}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`shrink-0 flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[exec.status] || 'bg-text-muted/20 text-text-muted'}`}>
            {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
            {exec.status}
            {isConnected && isRunning && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            )}
          </span>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              {exec.agent_name && (
                <span className="text-xs font-medium text-accent-cyan truncate max-w-[120px]">
                  {exec.agent_name}
                </span>
              )}
              <span className="text-xs text-text-muted">
                {exec.runtime}{exec.model ? ` · ${exec.model}` : ''}
                {isRunning && elapsed > 0 && (
                  <span className="ml-2">· {formatElapsed(elapsed)}</span>
                )}
                {toolCount > 0 && (
                  <span className="ml-2">· {toolCount} tools</span>
                )}
              </span>
            </div>
            <p className="text-sm text-text-primary truncate max-w-[400px] mt-0.5">
              {exec.task_id?.slice(0, 8) || exec.id?.slice(0, 8)} — {exec.market_id}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 shrink-0 ml-4">
          {exec.duration_ms && !isRunning && (
            <span className="hidden sm:flex items-center gap-1 text-xs text-text-muted">
              <Clock className="h-3 w-3" />
              {formatElapsed(exec.duration_ms)}
            </span>
          )}
          {exec.probability !== null && !isRunning && (
            <span className="text-sm font-mono text-text-secondary">
              P={(exec.probability * 100).toFixed(0)}% C={exec.confidence?.toFixed(2) || '?'}
            </span>
          )}
          {expanded ? <ChevronUp className="h-4 w-4 text-text-muted" /> : <ChevronDown className="h-4 w-4 text-text-muted" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border-subtle px-4 pb-4 pt-3 space-y-4">
          {(isRunning || isCompleted) && (
            <>
              <TimelineProgressBar steps={steps} />
              <ExecutionTimeline steps={steps} />
            </>
          )}

          {!isRunning && !isCompleted && (
            <div className="py-8 text-center">
              <Loader2 className="h-5 w-5 animate-spin text-text-muted mx-auto mb-2" />
              <p className="text-sm text-text-muted">Waiting for agent...</p>
            </div>
          )}

          {isCompleted && <ExecutionSummary exec={exec} />}
        </div>
      )}
    </div>
  );
}
import { Copy, FileText } from 'lucide-react';
import type { Execution } from '@/hooks/useExecutions';

interface Props {
  exec: Execution;
}

export default function ExecutionSummary({ exec }: Props) {
  const prob = exec.probability;
  const conf = exec.confidence;

  return (
    <div className="space-y-3 animate-fade-up">
      <div className="grid grid-cols-4 gap-2">
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Probability</p>
          <p className="mt-0.5 text-sm font-mono text-emerald-400">
            {prob !== null ? `${(prob * 100).toFixed(1)}%` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Confidence</p>
          <p className="mt-0.5 text-sm font-mono text-blue-400">
            {conf !== null ? `${(conf * 100).toFixed(1)}%` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Duration</p>
          <p className="mt-0.5 text-sm font-mono text-amber-400">
            {exec.duration_ms ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '—'}
          </p>
        </div>
        <div className="rounded-lg bg-bg-deep p-2.5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Tokens</p>
          <p className="mt-0.5 text-sm font-mono text-text-secondary">
            {exec.input_tokens > 0 ? `${exec.input_tokens}+${exec.output_tokens}` : '—'}
          </p>
        </div>
      </div>

      {exec.reasoning && (
        <div className="rounded-lg bg-bg-deep p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileText className="h-3 w-3 text-text-muted" />
            <span className="text-[10px] font-medium uppercase tracking-wider text-text-muted">Reasoning</span>
          </div>
          <p className="text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
            {exec.reasoning}
          </p>
        </div>
      )}

      {exec.status === 'failed' && exec.error_message && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
          <p className="text-xs text-red-400">{exec.error_message}</p>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => {
            if (exec.reasoning) {
              navigator.clipboard.writeText(exec.reasoning);
            }
          }}
          className="flex items-center gap-1 rounded-lg border border-border-subtle px-2.5 py-1.5 text-[10px] text-text-muted hover:text-text-primary hover:border-border-medium transition-colors"
        >
          <Copy className="h-3 w-3" />
          Copy reasoning
        </button>
      </div>
    </div>
  );
}

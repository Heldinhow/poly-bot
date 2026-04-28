import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { useExecutionSteps, ExecutionStep } from '@/hooks/useAudit';

const stepIcons: Record<string, string> = {
  text: '📝', thinking: '💭', tool_use: '🔧', tool_result: '✅', error: '❌', status: '📡', log: '📋',
};

function StepItem({ step }: { step: ExecutionStep }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg bg-bg-deep p-3">
      <button onClick={() => setExpanded(!expanded)} className="flex w-full items-center gap-2 text-left">
        <span className="text-xs">{stepIcons[step.step_type] || '•'}</span>
        <span className="text-xs font-mono uppercase text-text-muted">{step.step_type}</span>
        <span className="text-xs text-text-muted/50">#{step.seq}</span>
        {step.duration_ms && <span className="text-xs text-text-muted ml-auto">{(step.duration_ms / 1000).toFixed(1)}s</span>}
        {expanded ? <ChevronUp className="h-4 w-4 shrink-0 text-text-muted" /> : <ChevronDown className="h-4 w-4 shrink-0 text-text-muted" />}
      </button>
      {expanded && (
        <div className="mt-2 space-y-1">
          {step.content && <p className="text-sm text-text-secondary whitespace-pre-wrap">{step.content}</p>}
          {step.tool_name && <p className="text-xs text-text-muted">Tool: <span className="text-accent-cyan">{step.tool_name}</span></p>}
          {step.tool_output && <pre className="mt-1 max-h-32 overflow-auto rounded bg-surface-elevated p-2 text-xs text-text-secondary font-mono">{step.tool_output}</pre>}
        </div>
      )}
    </div>
  );
}

interface ExecutionInfo {
  id: string;
  status: string;
  agent_name?: string;
}

interface Props {
  executions: ExecutionInfo[];
  defaultExecutionId?: string;
}

export default function ExecutionStepsAccordion({ executions, defaultExecutionId }: Props) {
  const [open, setOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);

  const execId = executions[selectedIdx]?.id ?? defaultExecutionId ?? '';
  const { steps, isLoading } = useExecutionSteps(execId || null);

  if (!executions.length) return null;

  return (
    <div>
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted hover:text-text-primary">
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        Execution Steps {executions.length > 1 && `(${executions.length} runs)`}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {executions.length > 1 && (
            <div className="flex gap-1 flex-wrap">
              {executions.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedIdx(i)}
                  className={`rounded-lg px-2 py-1 text-xs ${
                    selectedIdx === i ? 'bg-accent-cyan/20 text-accent-cyan border border-accent-cyan/30' : 'text-text-muted hover:bg-surface-hover'
                  }`}
                >
                  Run {i + 1}
                </button>
              ))}
            </div>
          )}
          {isLoading ? <p className="text-sm text-text-muted">Loading steps...</p>
           : steps && steps.length > 0 ? steps.map(step => <StepItem key={step.id} step={step} />)
           : <p className="text-sm text-text-muted">No steps recorded.</p>}
        </div>
      )}
    </div>
  );
}

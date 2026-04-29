import { useState, useRef, useEffect, useCallback } from 'react';
import { ChevronDown, ChevronUp, Wrench, ArrowDown } from 'lucide-react';
import type { ExecutionStep } from '@/hooks/useExecutions';

const stepBadgeColors: Record<string, string> = {
  text: 'bg-emerald-500/20 text-emerald-400',
  thinking: 'bg-violet-500/20 text-violet-400',
  tool_use: 'bg-blue-500/20 text-blue-400',
  tool_result: 'bg-slate-500/20 text-slate-400',
  error: 'bg-red-500/20 text-red-400',
};

function StepRow({ step }: { step: ExecutionStep }) {
  const [expanded, setExpanded] = useState(false);
  const type = step.step_type;

  const summary = type === 'tool_use'
    ? `${step.tool_name || 'tool'}: ${JSON.stringify(step.tool_input || {}).slice(0, 60)}`
    : type === 'tool_result'
    ? (step.tool_output || '').slice(0, 80)
    : (step.content || '').slice(0, 150);

  const hasDetail = (step.content && step.content.length > 150)
    || (step.tool_output && step.tool_output.length > 80)
    || (step.tool_input && JSON.stringify(step.tool_input).length > 60);

  return (
    <div className="py-1.5">
      <button
        onClick={() => hasDetail && setExpanded(!expanded)}
        className="flex w-full items-start gap-2 text-left group"
      >
        <span className="shrink-0 text-[10px] text-text-muted/50 font-mono mt-0.5">
          #{step.seq}
        </span>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${stepBadgeColors[type] || 'bg-text-muted/20 text-text-muted'}`}>
          {type === 'tool_use' && <Wrench className="h-3 w-3 inline mr-1" />}
          {type === 'tool_use' ? step.tool_name || 'tool' : type === 'tool_result' ? 'result' : type}
        </span>
        <span className={`min-w-0 flex-1 text-xs truncate ${
          type === 'thinking' ? 'italic text-violet-300/60' :
          type === 'error' ? 'text-red-400' :
          'text-text-secondary'
        }`}>
          {summary || '\u00A0'}
        </span>
        {hasDetail && (
          <span className="shrink-0 text-text-muted/40 group-hover:text-text-muted">
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </span>
        )}
      </button>
      {expanded && (
        <div className="mt-1 ml-8 rounded-lg bg-surface-hover/50 p-2.5">
          {step.content && (
            <pre className="text-xs text-text-secondary whitespace-pre-wrap font-mono">{step.content}</pre>
          )}
          {step.tool_input && (
            <pre className="text-xs text-text-muted whitespace-pre-wrap font-mono mt-1">
              {JSON.stringify(step.tool_input, null, 2)}
            </pre>
          )}
          {step.tool_output && (
            <pre className="text-xs text-text-secondary whitespace-pre-wrap font-mono mt-1 max-h-48 overflow-auto">
              {step.tool_output.length > 4000 ? step.tool_output.slice(0, 4000) + '\n... [truncated]' : step.tool_output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

interface Props {
  steps: ExecutionStep[];
}

export default function ExecutionTimeline({ steps }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = useState(false);
  const prevLengthRef = useRef(steps.length);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
      setUserScrolledUp(false);
    }
  }, []);

  useEffect(() => {
    if (steps.length > prevLengthRef.current) {
      prevLengthRef.current = steps.length;
      if (!userScrolledUp) {
        scrollToBottom();
      }
    }
  }, [steps.length, userScrolledUp, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distFromBottom > 40) {
      setUserScrolledUp(true);
    } else {
      setUserScrolledUp(false);
    }
  }, []);

  if (steps.length === 0) {
    return <p className="text-xs text-text-muted py-4 text-center">Waiting for agent...</p>;
  }

  return (
    <div className="relative">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="max-h-72 overflow-y-auto"
      >
        {steps.map(step => (
          <StepRow key={`${step.seq}-${step.step_type}`} step={step} />
        ))}
      </div>
      {userScrolledUp && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 rounded-full bg-accent-cyan/20 border border-accent-cyan/30 px-3 py-1 text-xs text-accent-cyan hover:bg-accent-cyan/30 transition-colors"
        >
          <ArrowDown className="h-3 w-3" />
          Latest
        </button>
      )}
    </div>
  );
}

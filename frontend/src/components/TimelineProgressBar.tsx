import type { ExecutionStep } from '@/hooks/useExecutions';

const stepColors: Record<string, string> = {
  text: 'bg-emerald-500',
  thinking: 'bg-violet-500',
  tool_use: 'bg-blue-500',
  tool_result: 'bg-slate-500',
  error: 'bg-red-500',
};

const stepLabels: Record<string, string> = {
  text: 'Text',
  thinking: 'Thinking',
  tool_use: 'Tool Use',
  tool_result: 'Tool Result',
  error: 'Error',
};

interface Props {
  steps: ExecutionStep[];
}

export default function TimelineProgressBar({ steps }: Props) {
  if (steps.length === 0) return null;

  const counts: Record<string, number> = {};
  for (const s of steps) {
    counts[s.step_type] = (counts[s.step_type] || 0) + 1;
  }

  const total = steps.length;

  return (
    <div className="flex h-1 rounded-full overflow-hidden gap-px">
      {Object.entries(counts).map(([type, count]) => (
        <div
          key={type}
          className={`${stepColors[type] || 'bg-text-muted'} transition-all duration-200`}
          style={{ width: `${(count / total) * 100}%` }}
          title={`${stepLabels[type] || type}: ${count} steps`}
        />
      ))}
    </div>
  );
}
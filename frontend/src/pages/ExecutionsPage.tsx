import { useExecutions } from '@/hooks/useExecutions';
import { Activity } from 'lucide-react';
import LiveExecutionCard from '@/components/LiveExecutionCard';

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
          <LiveExecutionCard key={exec.id} exec={exec} />
        ))}
        {(!executions || executions.length === 0) && (
          <p className="text-sm text-text-muted">No executions yet.</p>
        )}
      </div>
    </div>
  );
}

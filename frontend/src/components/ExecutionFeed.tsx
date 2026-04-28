import { useExecutionFeed, ExecutionEvent } from '@/hooks/useExecutionFeed';
import { useEffect, useRef } from 'react';

const EVENT_COLORS: Record<string, string> = {
  'scan.started': 'text-amber-400',
  'market.filtered': 'text-slate-400',
  'market.analyzing': 'text-amber-400',
  'market.analyzed': 'text-cyan-400',
  'market.decided': 'text-blue-400',
  'bet.recorded': 'text-green-400',
  'bet.alert_sent': 'text-green-500',
  'portfolio.resolved': 'text-slate-300',
  'scan.completed': 'text-emerald-400',
  'scan.error': 'text-rose-400',
};

function EventEntry({ event }: { event: ExecutionEvent }) {
  const color = EVENT_COLORS[event.type] || 'text-slate-500';
  return (
    <div className={`text-xs font-mono ${color} py-0.5`}>
      <span className="text-slate-600 mr-2">{event.timestamp.split('T')[1]?.slice(0, 8)}</span>
      <span>[{event.type}]</span>
      <span className="ml-2">{event.message}</span>
    </div>
  );
}

export default function ExecutionFeed() {
  const { events, isConnected, scanStatus } = useExecutionFeed();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  return (
    <div className="rounded-xl border border-border-subtle bg-surface-elevated p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-slate-600'}`} />
          <span className="text-sm font-medium text-text-primary">
            {scanStatus === 'running' ? 'Scan Running' :
             scanStatus === 'error' ? 'Scan Error' : 'Scan Idle'}
          </span>
        </div>
        {events.length > 0 && (
          <span className="text-xs text-text-muted">{events.length} events</span>
        )}
      </div>

      {events.length === 0 ? (
        <p className="text-sm text-text-muted italic">
          {isConnected ? 'Waiting for scan to start...' : 'Connecting to live feed...'}
        </p>
      ) : (
        <div className="max-h-64 overflow-y-auto space-y-0.5 bg-black/20 rounded p-2">
          {events.map((event, i) => (
            <EventEntry key={i} event={event} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
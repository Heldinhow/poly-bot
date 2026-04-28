import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { TruthClaim } from '@/lib/api';

interface Props {
  claims: TruthClaim[];
}

function ClaimItem({ claim }: { claim: TruthClaim }) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round((claim.confidence_weight ?? 0) * 100);

  return (
    <div className="rounded-lg bg-bg-deep p-3">
      <button onClick={() => setExpanded(!expanded)} className="flex w-full items-start gap-2 text-left">
        <span className="shrink-0 text-xs text-text-muted">#{claim.order_index + 1}</span>
        <div className="min-w-0 flex-1">
          <p className={`text-sm ${expanded ? 'text-text-primary' : 'text-text-secondary truncate'}`}>
            {expanded ? claim.content : claim.content.slice(0, 120) + (claim.content.length > 120 ? '...' : '')}
          </p>
          {claim.source_reference && (
            <p className="mt-1 text-xs text-text-muted">Source: {claim.source_reference}</p>
          )}
          <div className="mt-2 flex items-center gap-2">
            <div className="h-1.5 w-16 rounded-full bg-surface-hover overflow-hidden">
              <div className="h-full bg-accent-cyan rounded-full" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs text-text-muted">{pct}% weight</span>
          </div>
        </div>
        {expanded ? <ChevronUp className="h-4 w-4 shrink-0 text-text-muted" /> : <ChevronDown className="h-4 w-4 shrink-0 text-text-muted" />}
      </button>
    </div>
  );
}

export default function TruthClaimsAccordion({ claims }: Props) {
  const [open, setOpen] = useState(false);
  if (!claims.length) return null;

  return (
    <div>
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-text-muted hover:text-text-primary">
        {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        Truth Claims ({claims.length})
      </button>
      {open && <div className="mt-2 space-y-2">{claims.map((c, i) => <ClaimItem key={i} claim={c} />)}</div>}
    </div>
  );
}
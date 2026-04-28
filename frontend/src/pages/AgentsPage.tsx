import { useState } from 'react';
import { useAgents } from '@/hooks/useAgents';
import { Bot, Plus, Trash2, Edit2, Save, X } from 'lucide-react';

export default function AgentsPage() {
  const { agents, isLoading, create, update, remove } = useAgents();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    runtime: 'claude',
    model: '',
    system_prompt: '',
    description: '',
  });

  const runtimes = ['claude', 'opencode', 'hermes', 'codex', 'gemini', 'pi', 'cursor-agent', 'kimi', 'kiro-cli', 'openclaw'];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(formData, { onSuccess: () => { setShowForm(false); setFormData({ name: '', runtime: 'claude', model: '', system_prompt: '', description: '' }); } });
  };

  const handleUpdate = (id: string, updates: Record<string, unknown>) => {
    update.mutate({ id, ...updates }, { onSuccess: () => setEditingId(null) });
  };

  if (isLoading) return <div className="p-8 text-text-muted">Loading agents...</div>;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <Bot className="h-6 w-6 text-accent-cyan" />
          Agents
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-accent-cyan px-4 py-2 text-sm font-medium text-black hover:bg-accent-cyan/90"
        >
          <Plus className="h-4 w-4" />
          New Agent
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-border-subtle bg-surface-elevated p-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input
              placeholder="Name"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              className="rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
              required
            />
            <select
              value={formData.runtime}
              onChange={e => setFormData({ ...formData, runtime: e.target.value })}
              className="rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
            >
              {runtimes.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
            <input
              placeholder="Model (optional)"
              value={formData.model}
              onChange={e => setFormData({ ...formData, model: e.target.value })}
              className="rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
            />
            <input
              placeholder="Description"
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              className="rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
            />
          </div>
          <textarea
            placeholder="System prompt..."
            value={formData.system_prompt}
            onChange={e => setFormData({ ...formData, system_prompt: e.target.value })}
            className="mt-4 w-full rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
            rows={4}
          />
          <div className="mt-4 flex gap-2">
            <button type="submit" className="rounded-lg bg-accent-cyan px-4 py-2 text-sm font-medium text-black">Create</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border border-border-subtle px-4 py-2 text-sm text-text-muted">Cancel</button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {agents?.map(agent => (
          <div key={agent.id} className="rounded-xl border border-border-subtle bg-surface-elevated p-4">
            {editingId === agent.id ? (
              <EditAgentForm agent={agent} onSave={handleUpdate} onCancel={() => setEditingId(null)} runtimes={runtimes} />
            ) : (
              <>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-text-primary">{agent.name}</h3>
                    <p className="text-xs text-text-muted">{agent.runtime} {agent.model && `· ${agent.model}`}</p>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => setEditingId(agent.id)} className="rounded p-1 hover:bg-surface-hover"><Edit2 className="h-4 w-4 text-text-muted" /></button>
                    <button onClick={() => remove.mutate(agent.id)} className="rounded p-1 hover:bg-surface-hover"><Trash2 className="h-4 w-4 text-text-muted" /></button>
                  </div>
                </div>
                <p className="mt-2 text-sm text-text-secondary line-clamp-2">{agent.description || 'No description'}</p>
                {agent.skills?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {agent.skills.map((skill: { id: string; name: string }) => (
                      <span key={skill.id} className="rounded-full bg-accent-cyan/10 px-2 py-0.5 text-xs text-accent-cyan">{skill.name}</span>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function EditAgentForm({ agent, onSave, onCancel, runtimes }: { agent: Record<string, unknown>; onSave: (id: string, data: Record<string, unknown>) => void; onCancel: () => void; runtimes: string[] }) {
  const [data, setData] = useState({
    name: agent.name as string,
    runtime: agent.runtime as string,
    model: (agent.model as string) || '',
    system_prompt: (agent.system_prompt as string) || '',
    description: (agent.description as string) || '',
  });

  return (
    <div>
      <div className="grid grid-cols-1 gap-2">
        <input value={data.name} onChange={e => setData({ ...data, name: e.target.value })} className="rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary" />
        <select value={data.runtime} onChange={e => setData({ ...data, runtime: e.target.value })} className="rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary">
          {runtimes.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <input value={data.model} onChange={e => setData({ ...data, model: e.target.value })} placeholder="Model" className="rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary" />
        <textarea value={data.system_prompt} onChange={e => setData({ ...data, system_prompt: e.target.value })} placeholder="System prompt" className="rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary" rows={3} />
      </div>
      <div className="mt-2 flex gap-2">
        <button onClick={() => onSave(agent.id as string, data)} className="flex items-center gap-1 rounded bg-accent-cyan px-3 py-1 text-xs font-medium text-black"><Save className="h-3 w-3" /> Save</button>
        <button onClick={onCancel} className="flex items-center gap-1 rounded border border-border-subtle px-3 py-1 text-xs text-text-muted"><X className="h-3 w-3" /> Cancel</button>
      </div>
    </div>
  );
}

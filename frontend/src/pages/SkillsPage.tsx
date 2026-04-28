import { useState } from 'react';
import { useSkills } from '@/hooks/useSkills';
import { FileText, Plus, Trash2, Save, X, Edit2 } from 'lucide-react';

export default function SkillsPage() {
  const { skills, isLoading, create, update, remove } = useSkills();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ name: '', content: '', description: '' });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(formData, { onSuccess: () => { setShowForm(false); setFormData({ name: '', content: '', description: '' }); } });
  };

  if (isLoading) return <div className="p-8 text-text-muted">Loading skills...</div>;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          <FileText className="h-6 w-6 text-accent-cyan" />
          Skills
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-accent-cyan px-4 py-2 text-sm font-medium text-black hover:bg-accent-cyan/90"
        >
          <Plus className="h-4 w-4" />
          New Skill
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-border-subtle bg-surface-elevated p-4">
          <input
            placeholder="Skill name"
            value={formData.name}
            onChange={e => setFormData({ ...formData, name: e.target.value })}
            className="mb-3 w-full rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
            required
          />
          <input
            placeholder="Description (optional)"
            value={formData.description}
            onChange={e => setFormData({ ...formData, description: e.target.value })}
            className="mb-3 w-full rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary"
          />
          <textarea
            placeholder="Markdown content..."
            value={formData.content}
            onChange={e => setFormData({ ...formData, content: e.target.value })}
            className="w-full rounded-lg border border-border-subtle bg-bg-deep px-3 py-2 text-sm text-text-primary font-mono"
            rows={10}
            required
          />
          <div className="mt-4 flex gap-2">
            <button type="submit" className="rounded-lg bg-accent-cyan px-4 py-2 text-sm font-medium text-black">Create</button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-lg border border-border-subtle px-4 py-2 text-sm text-text-muted">Cancel</button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {skills?.map(skill => (
          <div key={skill.id} className="rounded-xl border border-border-subtle bg-surface-elevated p-4">
            {editingId === skill.id ? (
              <EditSkillForm skill={skill} onSave={(id, data) => update.mutate({ id, ...data }, { onSuccess: () => setEditingId(null) })} onCancel={() => setEditingId(null)} />
            ) : (
              <>
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-text-primary">{skill.name}</h3>
                    {skill.description && <p className="text-xs text-text-muted">{skill.description}</p>}
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => setEditingId(skill.id)} className="rounded p-1 hover:bg-surface-hover"><Edit2 className="h-4 w-4 text-text-muted" /></button>
                    <button onClick={() => remove.mutate(skill.id)} className="rounded p-1 hover:bg-surface-hover"><Trash2 className="h-4 w-4 text-text-muted" /></button>
                  </div>
                </div>
                <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-bg-deep p-3 text-xs text-text-secondary font-mono whitespace-pre-wrap">{skill.content}</pre>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function EditSkillForm({ skill, onSave, onCancel }: { skill: Record<string, unknown>; onSave: (id: string, data: Record<string, unknown>) => void; onCancel: () => void }) {
  const [data, setData] = useState({
    name: skill.name as string,
    content: skill.content as string,
    description: (skill.description as string) || '',
  });

  return (
    <div>
      <input value={data.name} onChange={e => setData({ ...data, name: e.target.value })} className="mb-2 w-full rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary" />
      <input value={data.description} onChange={e => setData({ ...data, description: e.target.value })} placeholder="Description" className="mb-2 w-full rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary" />
      <textarea value={data.content} onChange={e => setData({ ...data, content: e.target.value })} className="w-full rounded border border-border-subtle bg-bg-deep px-2 py-1 text-sm text-text-primary font-mono" rows={8} />
      <div className="mt-2 flex gap-2">
        <button onClick={() => onSave(skill.id as string, data)} className="flex items-center gap-1 rounded bg-accent-cyan px-3 py-1 text-xs font-medium text-black"><Save className="h-3 w-3" /> Save</button>
        <button onClick={onCancel} className="flex items-center gap-1 rounded border border-border-subtle px-3 py-1 text-xs text-text-muted"><X className="h-3 w-3" /> Cancel</button>
      </div>
    </div>
  );
}

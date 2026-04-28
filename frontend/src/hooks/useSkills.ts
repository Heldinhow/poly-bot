import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8080';

export interface Skill {
  id: string;
  name: string;
  description: string | null;
  content: string;
  is_active: boolean;
  created_at: string;
}

async function fetchSkills(): Promise<Skill[]> {
  const res = await fetch(`${API_BASE}/api/skills`);
  if (!res.ok) throw new Error('Failed to fetch skills');
  return res.json();
}

async function createSkill(skill: Partial<Skill>): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/api/skills`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(skill),
  });
  if (!res.ok) throw new Error('Failed to create skill');
  return res.json();
}

async function updateSkill(id: string, skill: Partial<Skill>): Promise<void> {
  const res = await fetch(`${API_BASE}/api/skills/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(skill),
  });
  if (!res.ok) throw new Error('Failed to update skill');
}

async function deleteSkill(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/skills/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete skill');
}

export function useSkills() {
  const queryClient = useQueryClient();

  const { data: skills, isLoading, error } = useQuery({
    queryKey: ['skills'],
    queryFn: fetchSkills,
    refetchInterval: 5000,
  });

  const create = useMutation({
    mutationFn: createSkill,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['skills'] }),
  });

  const update = useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Skill>) => updateSkill(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['skills'] }),
  });

  const remove = useMutation({
    mutationFn: deleteSkill,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['skills'] }),
  });

  return { skills, isLoading, error, create, update, remove };
}

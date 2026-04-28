import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8080';

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  runtime: string;
  model: string | null;
  system_prompt: string | null;
  max_concurrent_tasks: number;
  max_retries: number;
  custom_args: string[];
  custom_env: Record<string, string>;
  is_active: boolean;
  skills: Skill[];
  created_at: string;
}

export interface Skill {
  id: string;
  name: string;
  description: string | null;
  content: string;
}

async function fetchAgents(): Promise<Agent[]> {
  const res = await fetch(`${API_BASE}/api/agents`);
  if (!res.ok) throw new Error('Failed to fetch agents');
  return res.json();
}

async function createAgent(agent: Partial<Agent>): Promise<{ id: string }> {
  const res = await fetch(`${API_BASE}/api/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(agent),
  });
  if (!res.ok) throw new Error('Failed to create agent');
  return res.json();
}

async function updateAgent(id: string, agent: Partial<Agent>): Promise<void> {
  const res = await fetch(`${API_BASE}/api/agents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(agent),
  });
  if (!res.ok) throw new Error('Failed to update agent');
}

async function deleteAgent(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/agents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete agent');
}

export function useAgents() {
  const queryClient = useQueryClient();

  const { data: agents, isLoading, error } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    refetchInterval: 5000,
  });

  const create = useMutation({
    mutationFn: createAgent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  const update = useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Partial<Agent>) => updateAgent(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  const remove = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['agents'] }),
  });

  return { agents, isLoading, error, create, update, remove };
}

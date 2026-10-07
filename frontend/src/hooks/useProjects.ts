import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { ProjectCreated } from '@/lib/types';

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: () => api.listProjects() });
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId!),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; llm_provider?: string; llm_model?: string }) =>
      api.createProject(body),
    onSuccess: (created: ProjectCreated) => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      qc.setQueryData(['projects', created.id], created);
    },
  });
}

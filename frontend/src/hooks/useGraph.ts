import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useGraph(projectId: string | undefined, graphId: string | undefined) {
  return useQuery({
    queryKey: ['projects', projectId, 'graphs', graphId],
    queryFn: () => api.getGraph(projectId!, graphId!),
    enabled: !!projectId && !!graphId,
  });
}

export function useSpecs(projectId: string | undefined) {
  return useQuery({
    queryKey: ['projects', projectId, 'specs'],
    queryFn: () => api.listSpecs(projectId!),
    enabled: !!projectId,
  });
}

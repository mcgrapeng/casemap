import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useProgress(projectId: string | undefined) {
  return useQuery({
    queryKey: ['projects', projectId, 'progress'],
    queryFn: () => api.getProgress(projectId!),
    enabled: !!projectId,
  });
}

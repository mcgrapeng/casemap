import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { CaseRecord } from '@/lib/types';

export function useCases(projectId: string | undefined, tag?: string) {
  return useQuery<CaseRecord[]>({
    queryKey: ['projects', projectId, 'cases', tag ?? 'all'],
    queryFn: () => api.listCases(projectId!, tag),
    enabled: !!projectId,
  });
}

export function useCase(projectId: string | undefined, caseId: string | undefined) {
  return useQuery<CaseRecord>({
    queryKey: ['projects', projectId, 'cases', caseId],
    queryFn: () => api.getCase(projectId!, caseId!),
    enabled: !!projectId && !!caseId,
  });
}

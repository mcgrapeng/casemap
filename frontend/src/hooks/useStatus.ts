import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { StatusPatch } from '@/lib/types';

export function usePatchStatus(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, body }: { caseId: string; body: StatusPatch }) =>
      api.patchStatus(projectId, caseId, body),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['projects', projectId, 'cases'] });
      qc.invalidateQueries({ queryKey: ['projects', projectId, 'progress'] });
      qc.invalidateQueries({ queryKey: ['projects', projectId, 'graphs'] });
      void vars;
    },
  });
}

export function useBulkImport(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entries: Parameters<typeof api.bulkImport>[1]) => api.bulkImport(projectId, entries),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects', projectId] });
    },
  });
}

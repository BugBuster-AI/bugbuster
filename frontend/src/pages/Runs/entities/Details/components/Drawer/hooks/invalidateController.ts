import { NEED_REFETCH_STATUSES } from '@Common/consts/run.ts';
import { ERunStatus } from '@Entities/runs/models';
import { runsQueries } from '@Entities/runs/queries';
import { useTestCaseStore } from '@Entities/test-case';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

export const useInvalidateController = (runId?: string, caseStatus?: ERunStatus) => {
    const testCase = useTestCaseStore((state) => state.currentCase)
    const queryClient = useQueryClient()
    const caseId = testCase?.group_run_case_id

    useEffect(() => {
        if (caseStatus && !NEED_REFETCH_STATUSES?.includes(caseStatus)) {
            queryClient.invalidateQueries({ queryKey: [...runsQueries.groupRuns(), runId] })
        }
    }, [caseStatus]);

    useEffect(() => {

        if (caseId && runId) {
            queryClient.setQueryData(['groupRunCaseMap', runId], caseId)
        }

        return () => {
            queryClient.removeQueries({ queryKey: ['groupRunCaseMap'] })
        }

    }, [caseId, runId]);
}

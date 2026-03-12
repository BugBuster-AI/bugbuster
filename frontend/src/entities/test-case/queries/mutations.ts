import { projectQueries } from '@Entities/project/queries';
import { projectKeys } from '@Entities/project/queries/query-keys.ts';
import { runsQueries } from '@Entities/runs/queries';
import { suiteQueries } from '@Entities/suite/queries';
import { TestCaseApi } from '@Entities/test-case/api';
import {
    IChangeCasePosition,
    ITestCaseCreateFromRecordPayload,
    ITestCaseCreatePayload,
    ITestCaseUpdatePayload
} from '@Entities/test-case/models';
import { caseQueries } from '@Entities/test-case/queries';
import { caseKeys } from '@Entities/test-case/queries/query-keys.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const testCaseApi = TestCaseApi.getInstance()

export const useCreateTestCase = () => {
    return useMutation({
        mutationKey: [caseKeys.index, caseKeys.create],
        mutationFn: (data: ITestCaseCreatePayload) => testCaseApi.create(data),
    });
};

export const useCreateCaseFromRecords = () => {
    return useMutation({
        mutationKey: [caseKeys.index, caseKeys.create],
        mutationFn: (data: ITestCaseCreateFromRecordPayload) => testCaseApi.createFromRecords(data),
    });
};

export const useDeleteTestCases = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationKey: [caseKeys.index, caseKeys.delete],
        mutationFn: (ids: string[]) => testCaseApi.deleteCasesById(ids),
        onSuccess: () => {
            const projectId = queryClient.getQueryData<string>([projectKeys.projectId]);

            if (projectId) {
                queryClient.invalidateQueries(projectQueries.byId(projectId as string))
            }
            queryClient.invalidateQueries(suiteQueries.userTree());
        }
    })
}

export const useUpdateTestCase = (noUpdate?: boolean) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationKey: [caseKeys.index, caseKeys.update],
        mutationFn: (data: ITestCaseUpdatePayload) => testCaseApi.update(data),
        onSuccess: (_value, data) => {
            if (!noUpdate) {
                queryClient.invalidateQueries(caseQueries.byId(data.case_id))
                queryClient.invalidateQueries(suiteQueries.userTree());
            }
        }
    });
}

export const useStopCaseRunning = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationKey: ['stop-case-running'],
        mutationFn: (runId: string) => testCaseApi.stopCase(runId),
        onSuccess: (_data, runId) => {
            queryClient.invalidateQueries({ ...runsQueries.runningCase(runId, {}) })
        }
    })
}

export const useChangeCasePosition = () => {

    // TODO: подумать над тем, как изолировать дерево сьютов от тест кейсов
    return useMutation({
        mutationFn: (data: IChangeCasePosition) => testCaseApi.changePosition(data),
    });
};

export const useCopyCase = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (caseId: string[]) => testCaseApi.copyCaseById(caseId),
        onSuccess: () => {
            const projectId = queryClient.getQueryData<string>([projectKeys.projectId]);

            if (projectId) {
                queryClient.invalidateQueries(projectQueries.byId(projectId as string))
            }
            queryClient.invalidateQueries(suiteQueries.userTree());
        }
    })
}


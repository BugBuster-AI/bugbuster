import { RunApi } from '@Entities/runs/api';
import { ICreateGroupedRunPayload, IDeleteCasesFromGroup } from '@Entities/runs/models';
import { ICompleteRunDto } from '@Entities/runs/models/complete-run.dto';
import { IPassStepDto } from '@Entities/runs/models/pass-step.dto.ts';
import { IStartGroupRunDto } from '@Entities/runs/models/start-group-run.ts';
import { runsQueries } from '@Entities/runs/queries';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const runsApi = RunApi.getInstance()

export const useStartGroupRun = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationKey: ['startGroupRun'],
        mutationFn: (data: IStartGroupRunDto) => runsApi.startGroupedRun(data),
        onSuccess: (_value, data) => {
            const id = data.group_run_id

            queryClient.invalidateQueries({ queryKey: ['groupRuns', id] })

            const caseId = queryClient.getQueryData<string>(['groupRunCaseMap', id]);

            if (caseId) {
                queryClient.invalidateQueries({
                    queryKey: ['runs', ['case_id', caseId]],
                    stale: true,
                    exact: false
                })
            }
        }
    })
}

export const useCreateGroupRun = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: ICreateGroupedRunPayload) => runsApi.createGroupedRun(data),
        onSuccess: (_value, oldData) => {
            const projectId = oldData.project_id

            queryClient.invalidateQueries({ ...runsQueries.groupedRunList({ project_id: projectId }) })
        }
    })
}

export const useEditGroupRun = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ id, data }: { id: string, data: ICreateGroupedRunPayload }) => runsApi.editGroupedRun(id, data),
        onSuccess: (_value, oldData) => {
            const projectId = oldData.data.project_id

            queryClient.invalidateQueries({ queryKey: ['groupRuns', oldData.id] })
            queryClient.invalidateQueries({ ...runsQueries.groupedRunList({ project_id: projectId }) })
        }
    })
}


export const useCompleteFailRunQuery = (groupRunId: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: ICompleteRunDto) => runsApi.competeRunCase(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['groupRuns', groupRunId] })

            const caseId = queryClient.getQueryData<string>(['groupRunCaseMap', groupRunId]);

            if (caseId) {

                queryClient.invalidateQueries({
                    queryKey: ['runs', ['case_id', caseId]],
                    stale: true,
                    exact: false
                })
            }
        }
    })
}

export const usePassTestStep = (groupRunId: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IPassStepDto) => runsApi.passCaseStepInRun(data),
        onSuccess: (newData) => {
            if (newData?.all_steps_passed) {
                queryClient.invalidateQueries({ queryKey: ['groupRuns', groupRunId] })
            }

            const caseId = queryClient.getQueryData<string>(['groupRunCaseMap', groupRunId]);

            if (caseId) {
                queryClient.invalidateQueries({
                    queryKey: ['runs', ['case_id', caseId]],
                    stale: true,
                    exact: false
                })
                queryClient.invalidateQueries({
                    queryKey: ['runningCase', caseId],
                    stale: true,
                    exact: false
                })
            }
        }
    })
}

export const useRemoveRunFromGroup = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IDeleteCasesFromGroup) => runsApi.deleteCasesFromGroup(data),
        onSuccess: (_data, response) => {
            queryClient.invalidateQueries({ queryKey: ['groupRuns', response.runId] })
        }
    })
}

export const useDeleteGroupRun = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (id: string) => runsApi.deleteGroupRun(id),
        onSuccess: () => {

            queryClient.invalidateQueries({ queryKey: [...runsQueries.groupRuns()] })
        }
    })
}

export const useCloneRun = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (ids: string[]) => runsApi.cloneRun(ids),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [...runsQueries.groupRuns()] })
        }
    })
}

export const usePatchSequentialOrder = (groupRunId: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (cases: { group_run_case_id: string; execution_order: number }[]) =>
            runsApi.patchSequentialOrder(groupRunId, cases),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['groupRuns', groupRunId] })
        }
    })
}

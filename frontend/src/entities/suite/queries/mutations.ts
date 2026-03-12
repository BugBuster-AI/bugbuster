import { projectQueries } from '@Entities/project/queries';
import { projectKeys } from '@Entities/project/queries/query-keys.ts';
import { SuiteApi } from '@Entities/suite/api';
import { IChangeSuitePosition, ICreateSuitePayload, IUpdateSuite } from '@Entities/suite/models';
import { suiteQueries } from '@Entities/suite/queries';
import { suiteKeys } from '@Entities/suite/queries/query-keys.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const suiteApi = SuiteApi.getInstance();

export const useUpdateSuite = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [suiteKeys.index, suiteKeys.update],
        mutationFn: (data: IUpdateSuite) => suiteApi.updateSuite(data),
        onSuccess: () => {
            queryClient.invalidateQueries(suiteQueries.userTree());
        }
    })
};

export const useCreateSuite = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [suiteKeys.index, suiteKeys.create],
        mutationFn: (data: ICreateSuitePayload) => suiteApi.createSuite(data),
        onSuccess: () => {
            const projectId = queryClient.getQueryData<string>([projectKeys.projectId]);

            if (projectId) {
                queryClient.invalidateQueries(projectQueries.byId(projectId as string))
            }
            queryClient.invalidateQueries(suiteQueries.userTree());
        }
    })
};

export const useDeleteSuite = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [suiteKeys.index, suiteKeys.create],
        mutationFn: (id: string) => suiteApi.delete(id),
        onSuccess: () => {
            const projectId = queryClient.getQueryData<string>([projectKeys.projectId]);

            if (projectId) {
                queryClient.invalidateQueries(projectQueries.byId(projectId as string))
            }
            queryClient.invalidateQueries(suiteQueries.userTree());
        },
    })
};

export const useChangePosition = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: IChangeSuitePosition) => suiteApi.changePosition(data),
        onSuccess: () => {
            queryClient.invalidateQueries(suiteQueries.userTree())
        }
    })
}

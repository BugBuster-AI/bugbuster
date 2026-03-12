import { billingQueries } from '@Entities/billing/queries';
import { WorkspaceApi } from '@Entities/workspace/api';
import { workspaceQueries } from '@Entities/workspace/queries/index.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const workspaceApi = WorkspaceApi.getInstance()

export const useChangeWorkspace = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (id: string) => workspaceApi.changeActiveWorkspace(id),
        onSuccess: () => {

            queryClient.invalidateQueries(billingQueries.tariffLimits())
        }
    })
}

export const useChangeWorkspaceName = (workspaceId: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (name: string) => workspaceApi.changeActiveWorkspaceName(name),
        onSuccess: () => {
            queryClient.invalidateQueries(workspaceQueries.byId(workspaceId))
        }
    })
}

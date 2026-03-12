import { WorkspaceApi } from '@Entities/workspace/api';
import { IWorkspaceLogPayload } from '@Entities/workspace/models/get-workspace-log.ts';
import { queryOptions } from '@tanstack/react-query';

const workspaceApi = WorkspaceApi.getInstance()

export const workspaceQueries = {
    all: () => ['workspaces'],

    list: () => queryOptions({
        queryKey: [...workspaceQueries.all()],
        queryFn: workspaceApi.getList,
    }),

    byId: (id: string) => ({
        queryKey: [...workspaceQueries.all(), id],
        queryFn: workspaceApi.getById.bind(null, id)
    }),

    logs: (id: string, params?: IWorkspaceLogPayload) => queryOptions({
        queryKey: ['workspace-logs', id, { ...params }],
        queryFn: () => workspaceApi.getWorkspaceLog(params)
    })
}

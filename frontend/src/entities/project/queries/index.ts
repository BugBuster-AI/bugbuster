import { IGetProjectListPayload } from '@Entities/project';
import { ProjectApi } from '@Entities/project/api';
import { projectKeys } from '@Entities/project/queries/query-keys.ts';
import { QueryObserverOptions, queryOptions } from '@tanstack/react-query';

const projectsApi = ProjectApi.getInstance()

export const projectQueries = {
    all: () => [projectKeys.index],
    list: (id?: string, params?: IGetProjectListPayload) => queryOptions({
        queryKey: [...projectQueries.all(), projectKeys.list, id, { ...params }],
        queryFn: () => projectsApi.getList(params),
    }),

    byId: (id: string) => queryOptions({
        queryKey: [projectKeys.byId, id],
        queryFn: () => projectsApi.getById(id),
        enabled: !!id
    }),

    freeStreams: (id?: string, options?: Partial<QueryObserverOptions<string, Error>>) => queryOptions({
        queryKey: [projectKeys.freeProjectStreams, id],
        queryFn: () => projectsApi.getFreeStreams(id),
        ...options
    })
}

export * from './mutations.ts'

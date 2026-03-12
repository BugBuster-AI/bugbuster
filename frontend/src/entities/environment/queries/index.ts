import { EnvironmentsApi } from '@Entities/environment/api';
import { envQueryKeys } from '@Entities/environment/queries';
import { queryOptions } from '@tanstack/react-query';

const envApi = EnvironmentsApi.getInstance()

export const envQueries = {
    all: () => [envQueryKeys.all],

    envList: (project_id: string) => queryOptions({
        queryKey: [...envQueries.all(), project_id],
        queryFn: () => envApi.getEnvList(project_id)
    }),

    osList: () => queryOptions({
        queryKey: [envQueryKeys.allOs],
        queryFn: envApi.getOs
    }),

    browserList: () => queryOptions({
        queryKey: [envQueryKeys.allBrowser],
        queryFn: envApi.getBrowsers
    }),

    envById: (id: string, enabled?: boolean) => queryOptions({
        queryKey: [...envQueries.all(), id],
        queryFn: () => envApi.getEnvById(id),
        enabled
    })
}

export * from './query-keys'

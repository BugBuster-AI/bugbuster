import { RecordsApi } from '@Entities/records/api';
import { IGetHappypassPayload } from '@Entities/records/models';
import { recordsKeys } from '@Entities/records/queries/query-keys';
import { queryOptions } from '@tanstack/react-query';

const recordsApi = RecordsApi.getInstance()

export const recordQueries = {
    all: () => [recordsKeys.index],

    list: ({ projectId }: { projectId: string }) => queryOptions({
        queryKey: [...recordQueries.all(), recordQueries.list, projectId],
        queryFn: () => recordsApi.getListHappypass({ projectId }),
        enabled: !!projectId
    }),

    showFull: (params?: IGetHappypassPayload, enabled = true) => queryOptions({
        queryKey: [recordsKeys.happypass, { ...params }],
        queryFn: () => recordsApi.getHappypass(params),
        enabled
    })
}

export * from './query-keys'

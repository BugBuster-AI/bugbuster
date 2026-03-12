import { StreamsApi } from '@Entities/stream/api';
import { IStreamsStatList } from '@Entities/stream/models';
import { streamQueryKeys } from '@Entities/stream/queries/query-keys';
import { QueryObserverOptions, queryOptions } from '@tanstack/react-query';

const streamApi = StreamsApi.getInstance()

export const streamQueries = {
    statList: (options?: Partial<QueryObserverOptions<IStreamsStatList, Error>>) => queryOptions({
        queryKey: [streamQueryKeys.statList],
        queryFn: () => streamApi.getStreamsStatistic(),
        ...options
    })
}

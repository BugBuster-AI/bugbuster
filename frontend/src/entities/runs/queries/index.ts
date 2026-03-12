import { NEED_REFETCH_STATUSES, REFETCH_RUN_INTERVAL } from '@Common/consts/run.ts';
import { RunApi } from '@Entities/runs/api';
import { IGetRunsPayload, IGroupedRunsParams, IGroupRunList, IRunById } from '@Entities/runs/models';
import { runQueryKeys } from '@Entities/runs/queries/query-keys';
import { keepPreviousData, QueryObserverOptions, queryOptions } from '@tanstack/react-query';
import entries from 'lodash/entries';
import get from 'lodash/get';
import includes from 'lodash/includes';

const runsApi = RunApi.getInstance()

interface IRunningCaseQueryOptions extends Partial<QueryObserverOptions<IRunById, Error>> {
    gcTime?: number
    onFetchingFinish?: () => void
    refetch?: boolean
    interval?: number
}

export const runsQueries = {
    all: () => [runQueryKeys.runs],
    groupRuns: () => [runQueryKeys.groupRuns],

    runs: (case_id: number) =>
        queryOptions({
            queryKey: [...runsQueries.all(), case_id],
            placeholderData: keepPreviousData
        }),

    runningCase: (runId: string, {
        refetch,
        gcTime,
        interval,
        onFetchingFinish,
        ...options
    }: IRunningCaseQueryOptions) => queryOptions({
        queryKey: [runQueryKeys.runningCase, runId],
        queryFn: () => runsApi.getRunById(runId),
        enabled: !!runId,
        gcTime: gcTime,
        refetchInterval: (query) => {
            if (refetch === false) {
                return undefined
            }
            const status = get(query, 'state.data.status', null)

            if (includes(NEED_REFETCH_STATUSES, status)) {
                return interval || REFETCH_RUN_INTERVAL
            } else if (!!status) {
                onFetchingFinish?.()
            }

            return undefined
        },
        ...options
    }),

    runList: (params?: IGetRunsPayload, enabled?: boolean) => queryOptions({
        queryKey: [...runsQueries.all(), ...entries(params)],
        queryFn: () => runsApi.getRuns(params),
        placeholderData: (data) => data,
        enabled
    }),

    groupedRunList: (params?: IGroupedRunsParams, enabled?: boolean, options?:
        Partial<QueryObserverOptions<IGroupRunList, Error>>) =>
        queryOptions({
            queryKey: [...runsQueries.groupRuns(), params?.group_run_id, ...entries(params)],
            queryFn: () => runsApi.getGroupedRuns(params),
            enabled,
            ...options
        }),

    statusList: () => queryOptions({
        queryKey: [runQueryKeys.statusList],
        queryFn: () => runsApi.getListStatuses(),
    }),

    freeStreams: (projectId: string, options?: Partial<QueryObserverOptions<string, Error>>) => queryOptions({
        queryKey: [runQueryKeys.freeStreams],
        queryFn: () => runsApi.getFreeStreamsForGrouprun(projectId),
        ...options
    })
}

export { useStartGroupRun } from './mutations'

import { getParamsArray } from '@Common/utils/common.ts';
import { SuiteApi } from '@Entities/suite/api';
import { IUserTreePayload } from '@Entities/suite/models';
import { suiteKeys } from '@Entities/suite/queries/query-keys.ts';
import { queryOptions } from '@tanstack/react-query';

const suiteApi = SuiteApi.getInstance()

export const suiteQueries = {
    all: () => [suiteKeys.index],

    userTree: (params?: IUserTreePayload, enabled?: boolean) => queryOptions({
        queryKey: [...suiteQueries.all(), suiteKeys.list, ...getParamsArray(params as {})],
        queryFn: suiteApi.getUserTree.bind(null, params),
        enabled,
    }),
}

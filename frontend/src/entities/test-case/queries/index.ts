import { ITestCase } from '@Entities/test-case/models';
import { QueryObserverOptions, queryOptions } from '@tanstack/react-query';
import { caseKeys } from './query-keys';
import { TestCaseApi } from '../api';

export * from './query-keys'
export * from './mutations.ts'

const testCaseApi = TestCaseApi.getInstance()

export const caseQueries = {
    all: () => [caseKeys.index],

    byId: (id: string, options?: Partial<QueryObserverOptions<ITestCase, Error>>) =>
        queryOptions({
            queryKey: [...caseQueries.all(), id],
            queryFn: testCaseApi.getById.bind(null, id),
            enabled: !!id,
            ...options
        }),

    caseTypes: () => queryOptions({
        queryKey: [caseKeys.caseTypes],
        queryFn: testCaseApi.getTestTypes
    }),

    finalTypes: () => queryOptions({
        queryKey: [caseKeys.finalTypes],
        queryFn: testCaseApi.getTestFinalStatuses
    })
}

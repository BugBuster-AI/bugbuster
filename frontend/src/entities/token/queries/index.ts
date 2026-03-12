import { queryOptions } from '@tanstack/react-query';
import { TokenApi } from '../api';
import { tokenQueryKeys } from './query-keys';

const tokenApi = TokenApi.getInstance();

export const tokenQueries = {
    all: () => queryOptions({
        queryKey: tokenQueryKeys.all,
        queryFn: () => tokenApi.getAll(),
    }),
};

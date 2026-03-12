import { AuthApi } from '@Entities/auth/api';
import { authKeys } from '@Entities/auth/queries/query-keys';
import { queryOptions } from '@tanstack/react-query';

const authApi = AuthApi.getInstance()

export const authQueries = {
    me: () => queryOptions({
        queryKey: [authKeys.me],
        queryFn: authApi.getUser
    }),
}


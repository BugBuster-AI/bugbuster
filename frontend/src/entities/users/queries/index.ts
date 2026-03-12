import { UsersApi } from '@Entities/users/api';
import { IUserListDto } from '@Entities/users/models/get-list.ts';
import { userQueryKeys } from '@Entities/users/queries/query-keys.ts';
import { queryOptions } from '@tanstack/react-query';

const usersApi = UsersApi.getInstance()

export const userQueries = {
    all: () => [userQueryKeys.users],

    list: (params?: IUserListDto) => queryOptions({
        queryKey: [...userQueries.all(), { ...params }],
        queryFn: usersApi.getList.bind(null, params),
    }),

    roles: () => queryOptions({
        queryKey: [userQueryKeys.roles],
        queryFn: usersApi.getRoles
    })
}

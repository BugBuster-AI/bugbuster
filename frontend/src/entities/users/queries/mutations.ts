import { UsersApi } from '@Entities/users/api';
import { IEditUserDto } from '@Entities/users/models/edit-user.dto.ts';
import { IInviteUserDto } from '@Entities/users/models/invite-user.dto.ts';
import { userQueries } from '@Entities/users/queries/index.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const usersApi = UsersApi.getInstance()

export const useInviteUser = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IInviteUserDto) => usersApi.inviteUser(data),
        onSuccess: () => {
            queryClient.invalidateQueries(userQueries.list())
        }
    })
}

export const useEditUser = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IEditUserDto) => usersApi.editUser(data),
        onSuccess: () => {
            queryClient.invalidateQueries(userQueries.list())
        }
    })
}

export const useDeleteUser = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (email: string) => usersApi.deleteUser(email),
        onSuccess: () => {
            queryClient.invalidateQueries(userQueries.list())
        }
    })
}

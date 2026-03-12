import { $api } from '@Common/api';
import { IUsersList } from '@Entities/users/models';
import { IEditUserDto } from '@Entities/users/models/edit-user.dto.ts';
import { IUserListDto } from '@Entities/users/models/get-list.ts';
import { IInviteUserDto } from '@Entities/users/models/invite-user.dto.ts';

export class UsersApi {
    private static instance: UsersApi | null

    public static getInstance (): UsersApi {
        if (!this.instance) {
            this.instance = new UsersApi()

            return this.instance
        }

        return this.instance
    }

    async getList (params?: IUserListDto): Promise<IUsersList> {
        return (await $api.get('workspace/get_workspace_memberships_list', { params })).data
    }

    async inviteUser (data: IInviteUserDto): Promise<string> {
        return (await $api.post('workspace/invite_user', data)).data
    }

    async editUser (data: IEditUserDto): Promise<string> {
        return (await $api.put('workspace/edit_user_workspace_membership', data)).data
    }

    async deleteUser (email: string): Promise<string> {
        return (await $api.delete(`workspace/remove_user_workspace_membership?email=${email}`)).data
    }

    async getRoles (): Promise<string[]> {
        return (await $api.get(`admin_content/list_roles`)).data
    }
}

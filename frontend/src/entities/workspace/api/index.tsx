import { $api } from '@Common/api';
import { IWorkspaceListItem } from '@Entities/workspace/models';
import { IWorkspaceLogPayload, IWorkspaceLogResponse } from '@Entities/workspace/models/get-workspace-log.ts';

export class WorkspaceApi {
    private static instance: WorkspaceApi | null

    public static getInstance (): WorkspaceApi {
        if (!this.instance) {
            this.instance = new WorkspaceApi()

            return this.instance
        }

        return this.instance
    }

    async getList (): Promise<IWorkspaceListItem[]> {
        return (await $api.get('workspace/get_list_user_workspaces')).data
    }

    async getById (id: string): Promise<IWorkspaceListItem[]> {
        return (await $api.get(`workspace/get_user_workspace_by_id?workspace_id=${id}`)).data
    }

    async changeActiveWorkspace (id: string) {
        return (await $api.post(`workspace/change_user_active_workspace?workspace_id=${id}`)).data
    }

    async changeActiveWorkspaceName (name: string) {
        return (await $api.post(`workspace/change_user_active_workspace_name?new_name=${name}`)).data
    }

    async acceptInvite (token: string) {
        return (await $api.post(`workspace/accept_invite_token?token=${token}`)).data
    }

    async getWorkspaceLog (params?: IWorkspaceLogPayload): Promise<IWorkspaceLogResponse> {
        return (await $api.get(`workspace/get_workspace_log`, { params })).data
    }
}

import { IPaginationResponse } from '@Common/types';
import { IWorkspaceLimit } from '@Entities/workspace/models';

export enum EUserStatus {
    ACTIVE = 'Active',
    INVITED = 'Invited'
}

export enum EUserRole {
    ADMIN = 'admin',
    MEMBER = 'member',
    READ_ONLY = 'read-only'
}

export interface IUserItem {
    workspace_id: string;
    user_id: string;
    first_name: string | null;
    last_name: string | null
    email: string;
    avatar_url: string | null
    role: EUserRole
    role_title: string;
    status: EUserStatus;
    last_action_date: string;
    workspace_name: string;
    workspace_owner: string;
    projects: IUserProject[]
}

export interface IUserProject {
    project_id: string;
    project_name: string
}

export interface IUserListItem extends Partial<IUserItem> {
}

export interface IUsersList extends IPaginationResponse {
    workspace_limits: IWorkspaceLimit[]
    items: IUserItem[]
}

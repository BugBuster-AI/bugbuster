import { EUserRole } from '@Entities/users/models';

export interface IWorkspaceListItem {
    workspace_id: string;
    workspace_name: string
    owner: string;
    role: EUserRole;
    role_title: string
    workspace_tariff_id: string,
    workspace_tariff_expiration: string,
    workspace_tariff_start_date: string,
    workspace_status: EWorkspaceStatus,
}

export interface IWorkspaceLimit {
    feature_name: string;
    limit_value: number;
    usage_count: number;
    remaining: number
}

export enum ELimitType {
    INVITE_USER = 'invite_user_workspace',
    START_GROUP_RUN = 'start_group_run',
    MAX_TASKS = 'max_concurrent_tasks',
    SAVE_HAPPY_PASS = 'save_happy_pass'
}

export enum EWorkspaceStatus {
    ACTIVE = 'Active',
    INACTIVE = 'Inactive'
}

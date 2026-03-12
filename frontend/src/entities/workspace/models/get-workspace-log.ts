import { IPaginationResponse } from '@Common/types';
import { IGroupedRun } from '@Entities/runs/models';

export interface IWorkspaceLogPayload {
    user_email?: string;
    start_dt?: string;
    end_dt?: string;
    limit?: string;
    offset?: string;
    host?: string;
}

export interface IWorkspaceLogItem {
    id: string;
    timestamp: string;
    user_id: string;
    user_email: string;
    user_username: string;
    workspace_id: string;
    method: string;
    endpoint_path: string;
    endpoint_name: string
    status_code: number
    params?: Partial<Omit<IGroupedRun, 'group_run_id'>> & {
        group_run_id: string
    }
}

export interface IWorkspaceLogResponse extends IPaginationResponse {
    items: IWorkspaceLogItem[]
}

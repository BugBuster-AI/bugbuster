import { IPaginationRequest } from '@Common/types';
import { EUserRole, EUserStatus } from '@Entities/users/models/index.ts';

export interface IUserListDto extends IPaginationRequest {
    role_filter?: EUserRole,
    status_filter?: EUserStatus,
    role_title_filter?: string,
    last_action_filter_start_dt?: string;
    last_action_filter_end_dt?: string
    page?: number;
    workspaceId?: string
}

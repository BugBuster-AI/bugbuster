import { EUserRole } from '@Entities/users/models';

export interface IUser {
    user_id: string;
    username: string;
    email: string;
    is_active: boolean;
    registered_at: string
    max_concurrent_tasks: number;
    active_workspace_id: string
    role: EUserRole,
}

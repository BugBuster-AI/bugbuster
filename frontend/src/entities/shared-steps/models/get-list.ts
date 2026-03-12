import { ISharedStep } from '@Entities/shared-steps/models/shared-steps.ts';

export type IGetSharedStepsListResponse = ISharedStep[]

export interface IGetSharedStepsListRequest {
    project_id: string
    search?: string
}

export interface IGetSharedStepsListByNameRequest {
    shared_steps_name: string;
    project_id: string
}

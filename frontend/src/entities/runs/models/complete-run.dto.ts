import { ERunStatus, IMedia } from '@Entities/runs/models';

export interface ICompleteRunDto {
    run_ids: string[]
    status?: ERunStatus
    comment?: string;
    attachments?: Omit<IMedia, 'url'>[]
    failed_step_index?: number
    reflection_step_index?: number
}

export type TCompleteRunResponse = string

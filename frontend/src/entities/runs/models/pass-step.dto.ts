import { IMedia } from '@Entities/runs/models/index.ts';

export interface IPassStepDto {
    run_id: string;
    passed_step_index: number;
    reflection_step_index?: number
    comment?: string;
    attachments?: IMedia[]
}

export interface IPassStepResponse {
    status: string;
    updated_run_id: string;
    step_index: number;
    all_steps_passed: boolean;
}

import { ISharedStep } from '@Entities/shared-steps/models/shared-steps.ts';

export interface ICreateSharedStepPayload
    extends Pick<ISharedStep, 'steps' | 'name' | 'description' | 'project_id'> {
}

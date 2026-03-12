import { ISharedStep } from '@Entities/shared-steps/models/shared-steps.ts';

export interface IUpdateSharedStepRequest extends Partial<Pick<ISharedStep, 'steps' | 'description' | 'name'>> {
    shared_steps_id: string
}

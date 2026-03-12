import { EStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';

export const GROUP_STEPS_ORDER = [
    EStepGroup.BEFORE_BROWSER,
    EStepGroup.BEFORE,
    EStepGroup.STEPS,
    EStepGroup.AFTER
] as EStepGroup[]


export const isSharedStep = (step?: { type?: EStepType, extra?: IExtraCaseType | null }): boolean => {
    return Boolean(step?.extra?.shared_step && step?.type !== EStepType.RESULT)
}

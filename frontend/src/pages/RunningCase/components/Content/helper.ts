import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IActionPlan } from '@Entities/test-case/models';
import { removeSlashes } from 'slashes';

export const getFormattedActionPlan = (actionPlan: IActionPlan | undefined, stepType: EStepType = EStepType.STEP) => {
    if (!actionPlan) {
        return undefined
    }

    const clonedActionPlan = { ...actionPlan }

    // Убираем служебные поля
    delete clonedActionPlan?.extra

    const strPlan = JSON.stringify(clonedActionPlan, null, 2)

    if (stepType === EStepType.API) {
        return removeSlashes(strPlan)
    }

    return strPlan
}

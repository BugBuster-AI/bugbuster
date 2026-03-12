
import { EStepType } from '@Entities/test-case/components/Form/models';
import { ILocalStepData } from '@Entities/test-case/models';
import { IMedia, IRunStep } from '../models';

export const isShowBeforeImage = (
    step?: Partial<IRunStep> | null, 
    beforeImage?: IMedia | null, 
    localVer: boolean = false
): boolean => {

    if (localVer) {
        if (!beforeImage || !beforeImage?.url) return false

        const localStep = step as ILocalStepData
        const isExpectedResult = localStep?.type === EStepType.RESULT

        if (isExpectedResult) {
            const useSingleScreenshot = localStep?.extra?.use_single_screenshot;

            if (useSingleScreenshot === false) {
                return true
            }
  
            return false
        }

        return true
    }

    const isExpectedResult = step?.step_type === EStepType.RESULT 

    if (isExpectedResult) {
        const useSingleScreenshot = step?.extra?.use_single_screenshot;

        if (useSingleScreenshot === false) {
            return true
        }

        if (!beforeImage || !beforeImage?.url) return false

        return false
    }

    return true
}

interface IOptions {
    isEditing?: boolean
}

export const isShowAfterImage = (
    step?: Partial<IRunStep> | null, 
    options?: IOptions
) => {
    const after = step?.after
    const isEditing = options?.isEditing
    const isExpectedResult = step?.step_type === EStepType.RESULT

    if (isExpectedResult) {
        if (isEditing && Boolean(after)) {
            return true
        }
    }

    return Boolean(after) && !isEditing
}

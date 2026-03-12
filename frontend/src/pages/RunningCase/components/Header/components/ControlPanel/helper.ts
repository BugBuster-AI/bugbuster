import { convertImageToBase64 } from '@Common/utils/base64';
import { replaceTemplateVariables } from '@Common/utils/variables';
import { CommonApi } from '@Entities/common/api';
import { IRunStep } from '@Entities/runs/models';
import { IEditingStep } from '@Pages/RunningCase/store/models.ts';
import cloneDeep from 'lodash/cloneDeep';
import compact from 'lodash/compact';
import find from 'lodash/find';
import map from 'lodash/map';

const commonApi = CommonApi.getInstance()

export const createNewContextScreenshots = async (steps: IEditingStep[]) => {
    const clonedSteps = cloneDeep(steps)

    for (const stepItem of clonedSteps) {
        const step = stepItem.step

        try {
            if (step.contextScreenshotMode?.isEnabled 
            && step?.contextScreenshotMode?.isNewCoordinates 
            && step?.contextScreenshotMode?.coordinates) {
                const originImage = await convertImageToBase64(step?.before?.url ?? '')
                const coordinates = step.contextScreenshotMode.coordinates
                const response = await commonApi.createContextScreenshot({
                    image_base64_string: originImage,
                    x1: Math.floor(coordinates.x),
                    y1: Math.floor(coordinates.y),
                    x2: Math.floor(coordinates.x + coordinates.width),
                    y2: Math.floor(coordinates.y + coordinates.height),
                })

                step.extra = {
                    ...step.extra,
                    context_screenshot_path: response
                }
            }
        } catch {
            return {
                status: 0,
                steps
            }
        }
    }

    return {
        status: 1,
        steps: clonedSteps
    }
}

export const mergeSteps = (runSteps: IRunStep[], editingSteps: IEditingStep[], variables?: Record<string, string>) => {
    return map(runSteps, (step) => {
        const findStep = find(editingSteps, (item) => item.id === step.localUUID)

        if (findStep) {
            return {
                ...findStep.step,
                original_step_description: replaceTemplateVariables(
                    findStep.step.original_step_description, variables || {}
                ),
                isEdited: true
            }
        }

        return step
    })
}

export const findStepsByError = (steps: IRunStep[], error: Record<string | number, string>) => {
    if (typeof error === 'string') {
        return []
    }

    // reject(steps, (item) => item.step_type === EStepType.RESULT)
    return compact(map(steps, (step) => {
        const stepIndex = step.localIndexStep || -1
        const currentError = error?.[stepIndex]

        if (currentError) {
            return {
                ...step,
                error: currentError
            }
        }

        return undefined
    }))
}

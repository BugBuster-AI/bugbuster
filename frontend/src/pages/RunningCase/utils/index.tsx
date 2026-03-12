import { IRunById, IRunStep } from '@Entities/runs/models';
import { generateLocalUUID } from '@Pages/RunningCase/store/helper';
import { ICommitedStepsData } from '@Pages/RunningCase/store/models.ts';
import find from 'lodash/find';
import map from 'lodash/map';
import reduce from 'lodash/reduce';
import some from 'lodash/some';

export const getStepId = ({ index, group, reflectionIndex }: {
    index: number,
    group: string,
    reflectionIndex?: number
}) => {
    return `${group}.${index}.${reflectionIndex ?? false}`
}

export const getIndexFromStepId = (id?: string) => {
    if (!id) {
        return null
    }
    const parts = id.split('.')

    if (parts.length < 2) return null

    const index = parseInt(parts[1], 10)

    if (isNaN(index)) return null

    return index
}

export const decodeStepId = (id: string) => {
    const parts = id.split('.')

    if (parts.length < 2) {
        return {
            group: null,
            index: null,
            reflectionIndex: null
        }
    }

    const group = parts[0]
    const index = parseInt(parts[1], 10)
    const reflectionIndex = parts.length >=3 ? parseInt(parts[2], 10) : null

    return {
        group,
        index: isNaN(index) ? null : index,
        reflectionIndex: isNaN(reflectionIndex as number) ? null : reflectionIndex
    }
}

export const convertGroupToLocal = (value?: string) => {
    switch (value) {
        case 'before_browser':
            return 'before_browser_start'
        case 'before':
            return 'before_steps'
        case 'step':
            return 'steps'
        case 'after':
            return 'after_steps'
        default:
            return value ?? ''
    }
}

export const commitSteps = (run?: IRunById): ICommitedStepsData => {
    if (!run) return {}

    return reduce(run.steps, (acc, step) => {
        const stepId = getStepId({
            index: step.index_step,
            group: convertGroupToLocal(step.step_group),
        })

        acc[stepId] = {
            name: step.original_step_description,
            isEdited: false
        }

        return acc
    }, {})
}

// Превращение reflection в отдельные степы с уникальными id
export const prepareRunWithStepIds = (run?: IRunById, currentRun?: IRunById) => {
    if (!run) return null

    /*
     * Если есть локально созданные шаги, используем currentRun.steps как основу
     * и только обновляем их данными с сервера
     */
    const hasLocalSteps = some(currentRun?.steps, (step) => step.isLocalCreated)
    
    if (hasLocalSteps && currentRun) {
        // Обновляем только шаги с сервера, сохраняя локальные
        const updatedSteps = map(currentRun.steps, (step) => {
            if (step.isLocalCreated) {
                // Локальные шаги не трогаем
                return step
            }
            
            // Для серверных шагов обновляем данные с сервера по UUID
            const serverStep = find(run.steps, (s) => s.localUUID === step.localUUID)
            
            if (serverStep && step.isEdited) {
                // Если шаг редактируется, оставляем отредактированную версию
                return step
            }
            
            if (serverStep) {
                // Обновляем данные с сервера
                return {
                    ...serverStep,
                    localId: step.localId,
                    localUUID: step.localUUID,
                    localIndexStep: step.localIndexStep ?? step.index_step,
                    index_step: step.index_step,
                    contextScreenshotMode: {
                        isEnabled: serverStep?.extra?.context_screenshot_used
                    }
                } as IRunStep
            }
            
            return step
        })
        
        return {
            ...run,
            steps: updatedSteps
        } as IRunById
    }

    // Стандартная логика для первой загрузки (без локальных шагов)
    const steps = reduce(run.steps, (acc, step, index) => {
        const indexStep = index
        const stepId = getStepId({
            index: indexStep,
            group: convertGroupToLocal(step.step_group),
        })

        // Сначала ищем по UUID (если есть), потом по localId
        const currentStep = step.localUUID 
            ? find(currentRun?.steps, (item) => item.localUUID === step.localUUID)
            : find(currentRun?.steps, (item) => item.localId === stepId)


        const stepWithId = currentStep?.isEdited ? currentStep : {
            ...step,
            localId: stepId,
            localUUID: step.localUUID || currentStep?.localUUID || generateLocalUUID(),
            localIndexStep: currentStep?.localIndexStep ?? indexStep,
            index_step: indexStep,
            contextScreenshotMode: {
                // если включен, то включаем на фронтенде
                isEnabled: step?.extra?.context_screenshot_used
            }
        } as IRunStep

        acc.push(stepWithId)

        return acc
    }, [] as IRunStep[])

    return {
        ...run,
        steps
    } as IRunById

}

export const base64ToImageUrl = (base64String?: string): string => {
    if (!base64String) return ''
    // Проверяем, что строка является валидным base64 изображением
    if (!base64String.startsWith('data:image/')) {
        return base64String
    }

    // Разделяем data URL на части
    const parts = base64String.split(';base64,');

    if (parts.length !== 2) {
        return base64String
    }

    const contentType = parts[0].split(':')[1];
    const base64Data = parts[1];

    // Декодируем base64 в бинарные данные
    const byteCharacters = atob(base64Data);
    const byteArrays = [];

    for (let offset = 0; offset < byteCharacters.length; offset += 512) {
        const slice = byteCharacters.slice(offset, offset + 512);

        const byteNumbers = new Array(slice.length);

        for (let i = 0; i < slice.length; i++) {
            byteNumbers[i] = slice.charCodeAt(i);
        }

        const byteArray = new Uint8Array(byteNumbers);

        // @ts-ignore
        byteArrays.push(byteArray);
    }

    // Создаем Blob и URL
    const blob = new Blob(byteArrays, { type: contentType });

    return URL.createObjectURL(blob);
}

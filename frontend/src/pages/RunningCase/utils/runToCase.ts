import { IRunById, TStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models';
import { ITestCase, ITestCaseStep } from '@Entities/test-case/models';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables';
import { convertGroupToLocal } from '@Pages/RunningCase/utils/index.tsx';
import isString from 'lodash/isString';
import nth from 'lodash/nth';
import reduce from 'lodash/reduce';
import size from 'lodash/size';

export const runToCase = (run: IRunById): ITestCase => {
    const runCase = run?.case?.original_case ?? run.case
    const caseSteps =
        // @ts-ignore
        [...runCase?.before_browser_start, ...runCase?.before_steps, ...runCase?.steps, ...runCase?.after_steps]

    const stepsData = run.steps

    const combinedSteps = reduce(stepsData, (acc, item) => {
        const currentGroup = convertGroupToLocal(item.step_group)
        const currentIndex = item.index_step
        let currentCaseStep: ITestCaseStep

        if (item.isLocalCreated) {
            currentCaseStep = {} as ITestCaseStep
        } else {
            currentCaseStep = nth(caseSteps, currentIndex ?? -1) as ITestCaseStep
        }


        // const currentEditedStep = find(editedSteps, (edited) => edited.id === item.localUUID)
        let newStep

        // const currentEditedData = currentEditedStep?.step

        const preparedExtra = {
            ...currentCaseStep?.extra
        } as IExtraCaseType

        /*
         * если включен режим контекстного скриншота, то добавляем путь к скриншоту в extra
         * if (currentEditedData?.contextScreenshotMode?.isEnabled) {
         */
        if (item?.contextScreenshotMode?.isEnabled) {
            preparedExtra.context_screenshot_path = 
            item?.extra?.context_screenshot_path || undefined
            // currentEditedData?.extra?.context_screenshot_path || undefined
            preparedExtra.context_screenshot_used = true
        } else {
            preparedExtra.context_screenshot_path = null
            preparedExtra.context_screenshot_used = false
        }
        
        /*
         * Для expected_result шагов сохраняем use_single_screenshot только если оно явно задано
         * if (item.step_type === EStepType.RESULT && currentEditedData) {
         */
        if (item.step_type === EStepType.RESULT && item) {
            // const useSingleScreenshotValue = currentEditedData?.extra?.use_single_screenshot;
            const useSingleScreenshotValue = item?.extra?.use_single_screenshot;
            
            if (useSingleScreenshotValue !== undefined) {
                preparedExtra.use_single_screenshot = useSingleScreenshotValue;
            }
        }

        // устанавливаем newStep
        if (isString(currentCaseStep)) {
            newStep = {
                type: EStepType.STEP,
                value: item?.raw_step_description || currentCaseStep,
                extra: preparedExtra
            }
        } else {
            newStep = (item ? {
                ...currentCaseStep,
                /*
                 *  TODO: разобраться почему step, а не action
                 */
                //@ts-ignore
                type: (item.step_type === 'step' ? EStepType.STEP : item.step_type) ?? currentCaseStep.type,
                value: item.raw_step_description,
                extra: preparedExtra
            } : currentCaseStep) as ITestCaseStep
        }

        // пушим newStep в конкретную группу 
        if (size(acc?.[currentGroup])) {
            acc[currentGroup].push(newStep)
        } else {
            acc[currentGroup] = []
            acc[currentGroup].push(newStep)
        }

        return acc
    }, {} as Record<TStepGroup, ITestCaseStep[]>)

    //@ts-ignore
    return {
        ...runCase,
        // original_case: run?.case?.original_case,
        ...combinedSteps
    }
}

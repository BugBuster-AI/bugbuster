import { PROGRESS_STATUSES } from '@Common/consts/run.ts';
import { groupLocalSteps } from '@Common/utils';
import { ERunStatus, IRunById, IRunStep } from '@Entities/runs/models';
import { convertStepType } from '@Entities/runs/utils/stepType.ts';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ELocalStepStatus, ILocalRunData, ILocalStepData } from '@Entities/test-case/models';
import find from 'lodash/find';
import get from 'lodash/get';
import includes from 'lodash/includes';
import isNil from 'lodash/isNil';
import map from 'lodash/map';
import reduce from 'lodash/reduce';
import size from 'lodash/size';
import { useMemo } from 'react';

interface IReturnData extends ILocalRunData {
    loadingStep?: ILocalStepData | null
}

const convertLocalStepStatus = (status?: ERunStatus | boolean): ELocalStepStatus => {
    if (isNil(status)) {
        return ELocalStepStatus.UNTESTED
    }
    switch (status) {
        case ERunStatus.FAILED:
            return ELocalStepStatus.FAILED
        case ERunStatus.PASSED:
            return ELocalStepStatus.SUCCESS
        case false:
            return ELocalStepStatus.FAILED
        case true:
            return ELocalStepStatus.SUCCESS
        default:
            return ELocalStepStatus.UNTESTED
    }
}

const prepareRunSteps = (steps?: IRunStep[]): ILocalStepData[] => {
    if (!steps) return []

    return reduce(steps, (result, item) => {
        const results = get(item, 'validation_result')
        // const hasResults = size(results) > 0

        /*
         * const stepStatus = convertLocalStepStatus(getRealStepStatus({
         *     reflectionResults: results,
         *     status: item.status_step,
         * }))
         */
        const stepStatus = convertLocalStepStatus(item.status_step)

        let resultSteps: ILocalStepData[] = []

        const description = item.step_type === EStepType.RESULT ? results?.reflection_description : get(item, 'comment')
        /*
         * if (hasResults) {
         *     forEach(results, (el, index) => {
         *         const itemName = item.reflection_steps?.[index]
         *
         *         const needFullData = stepStatus !== ELocalStepStatus.FAILED && el.reflection_result !== null
         *         const fullData = {
         *             beforeImage: item.before_annotated_url,
         *             afterImage: item.after,
         *         } as ILocalStepData
         *
         *         const formattedEl = {
         *             name: el?.reflection_step || itemName,
         *             type: EStepType.RESULT,
         *             group: item.step_group,
         *             description: el.reflection_description,
         *             partNum: el.part_num,
         *             title: el?.reflection_title,
         *             status: convertLocalStepStatus(el.reflection_result),
         *             partAll: item?.part_all,
         *             attachments: item.attachments,
         *             extra: get(el, 'extra', undefined),
         *             // extra: item.extra,
         *             ...(needFullData ? fullData : {}),
         *         } as ILocalStepData
         *
         *         resultSteps.push(formattedEl)
         *     })
         * }
         */

        const formattedStep = {
            name: get(item, 'original_step_description', null),
            actionType: get(item, 'action'),
            afterImage: get(item, 'after'),
            beforeImage: get(item, 'before_annotated_url'),
            type: convertStepType(item.step_type, true),
            description,
            completeTime: item.step_time,
            partNum: item.part_num,
            partAll: item.part_all,
            group: item.step_group,
            status: stepStatus,
            attachments: item.attachments,
            extra: item.extra,
        } as ILocalStepData

        result.push(formattedStep)

        if (size(resultSteps)) {
            result.push(...resultSteps)
        }

        return result
    }, [] as ILocalStepData[])
}

interface IProps {
    run?: IRunById
}

export const useLocalRunStepsData = ({ run }: IProps): IReturnData => {

    const getLoadingStep = (steps?: ILocalStepData[]) => {
        if (!steps) return null
        const firstUntested = find(steps, ['status', ELocalStepStatus.UNTESTED])

        if (find(steps, { status: ELocalStepStatus.FAILED })) {
            return null
        }

        if (includes(PROGRESS_STATUSES, run?.status)) {
            return firstUntested
        }

        return null
    }

    const formatSteps = (steps: ILocalStepData[], loadingStep?: ILocalStepData | null) => {
        if (!loadingStep) {
            return steps
        }

        return map(steps, (item) => ({ isLoading: loadingStep?.partNum === item.partNum, ...item } as ILocalStepData))
    }

    const localSteps = useMemo(() => prepareRunSteps(run?.steps), [run])
    const loadingStep = useMemo(() => getLoadingStep(localSteps), [run])
    const formattedSteps = formatSteps(localSteps, loadingStep)
    const groupedSteps = useMemo(() => groupLocalSteps(formattedSteps), [formattedSteps])

    return {
        steps: groupedSteps,
        status: run?.status,
        loadingStep: loadingStep
    }
}

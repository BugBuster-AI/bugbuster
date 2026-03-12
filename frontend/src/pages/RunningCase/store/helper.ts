import { EStatusIndicator } from '@Common/components';
import { ERunStatus, IRunById, IRunStep, TStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import size from 'lodash/size';

/**
 * Генерирует UUID для локальной идентификации шагов
 */
export const generateLocalUUID = (): string => {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

export const getLogStatus = (isSuccess?: boolean): EStatusIndicator => {
    if (isSuccess) {
        return EStatusIndicator.SUCCESS
    }

    return EStatusIndicator.ERROR
}

export const getRunKey = (run?: IRunById): string => {
    if (!run) return ''

    return `${run.run_id} ${size(run.steps)} ${run.status} ${run.run_summary} ${run.end_dt}`
}

/**
 * Создает пустой шаг для вставки в ран
 */
export const createEmptyStep = (params: {
    stepId: string;
    index: number;
    partNum: number;
    partAll: number;
    stepGroup: TStepGroup;
    stepType: EStepType;
    beforeStep: IRunStep;
}): IRunStep => {
    const { stepId, index, partNum, partAll, stepGroup, stepType, beforeStep } = params

    return {
        index_step: index,
        localId: stepId,
        localUUID: generateLocalUUID(),
        part_num: partNum,
        part_all: partAll,
        step_group: stepGroup,
        step_type: stepType,
        status_step: ERunStatus.UNTESTED,
        original_step_description: '',
        raw_step_description: '',
        step_description: '',
        localIndexStep: index,
        action: '',
        coords: [],
        text: '',
        model_time: '0',
        step_time: '0.00',
        reflection_steps: [],
        reflection_title: null,
        validation_result: null,
        before_annotated_url: stepType === EStepType.STEP ? beforeStep.after : beforeStep.before_annotated_url,
        before: stepType === EStepType.STEP ? beforeStep.after : beforeStep.before,
        after: beforeStep.after,
        isLocalCreated: true,
        extra: stepType === EStepType.RESULT ? { use_single_screenshot: true } : null,
    }
}


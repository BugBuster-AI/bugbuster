import { IRunStep } from '@Entities/runs/models';

export interface IGroupedStep {
    type: 'single' | 'shared_group';
    step?: IRunStep;
    steps?: IRunStep[];
    sharedStepId?: string;
    sharedStepIndex?: number;
}

/**
 * Группирует степы, объединяя shared steps в группы
 * @param steps - массив степов
 * @returns массив сгруппированных степов
 */
export const groupSharedSteps = (steps: IRunStep[]): IGroupedStep[] => {
    const result: IGroupedStep[] = [];
    let i = 0;

    while (i < steps.length) {
        const currentStep = steps[i];
        const sharedStepId = currentStep.extra?.shared_step_id;
        const sharedStepIndex = currentStep.extra?.shared_step_group_index;

        // Если это не shared step, добавляем как обычный степ
        if (!sharedStepId || sharedStepIndex === undefined) {
            result.push({
                type: 'single',
                step: currentStep,
            });
            i++;
            continue;
        }

        // Если это shared step, собираем все степы этой группы
        const groupSteps: IRunStep[] = [currentStep];
        let j = i + 1;

        // Ищем все следующие степы с тем же shared_step_id и shared_step_index
        while (j < steps.length) {
            const nextStep = steps[j];

            if (
                nextStep.extra?.shared_step_id === sharedStepId &&
                nextStep.extra?.shared_step_group_index === sharedStepIndex
            ) {
                groupSteps.push(nextStep);
                j++;
            } else {
                break;
            }
        }

        // Добавляем группу
        result.push({
            type: 'shared_group',
            steps: groupSteps,
            sharedStepId,
            sharedStepIndex,
        });

        i = j;
    }

    return result;
};

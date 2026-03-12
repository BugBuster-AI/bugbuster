import { EStatusIndicator } from '@Common/components';
import { ERunStatus } from '@Entities/runs/models';
import { StepProps } from 'antd';
import compact from 'lodash/compact'
import isEmpty from 'lodash/isEmpty';

export const getParamsArray = (params?: Record<string, unknown>) => {
    if (isEmpty(params) || !params) {
        return []
    }

    return compact(Object.values(params))
}

// Трансформация статусов рана в статусы step из Antd
export const getAntStepStatus = (status: ERunStatus): StepProps['status'] => {
    switch (status) {
        case ERunStatus.PASSED:
            return 'finish'
        case ERunStatus.FAILED:
            return 'error'
        case ERunStatus.IN_PROGRESS:
            return 'wait'
        default:
            return 'wait'
    }
}

// Трансформация статусов рана в статусы для индикатора
export const getRunStatusToIndicator = (status?: ERunStatus): EStatusIndicator => {
    switch (status) {
        case ERunStatus.PASSED:
            return EStatusIndicator.SUCCESS
        case ERunStatus.FAILED:
            return EStatusIndicator.ERROR
        default:
            return EStatusIndicator.IDLE
    }
}


export function insert<T> (array: T[], index: number, ...elements: T[]): T[] {
    // Создаем копию массива, чтобы избежать мутации исходного
    const newArray = [...array];

    // Вставляем элементы на указанную позицию
    newArray.splice(index, 0, ...elements);

    return newArray;
}

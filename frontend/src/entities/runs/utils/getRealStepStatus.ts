import { ERunStatus, EStepStatus, IReflectionResult } from '@Entities/runs/models';
import filter from 'lodash/filter';
import isNil from 'lodash/isNil';
import isUndefined from 'lodash/isUndefined';
import size from 'lodash/size';

interface IProps {
    status?: ERunStatus
    reflectionResults?: IReflectionResult[] | null
}

export const getRealStepStatus = ({ status, reflectionResults }: IProps): ERunStatus => {
    const firstReflectionStep = reflectionResults?.[0]
    const isFailed = status === ERunStatus.FAILED && isUndefined(firstReflectionStep)

    const isUntested = isNil(status)

    if (isUntested) {
        return ERunStatus.UNTESTED
    }
    /**
     * HINT: поддержка старого формата с false
     */
    const hasFalseResult = size(filter(reflectionResults, (item) =>
        /*
         * HINT: поддержка старого формата
         */
        // @ts-ignore
        item.reflection_result === EStepStatus.FAILED || item.reflection_result == false
    )) > 0

    const isSuccess = status === ERunStatus.FAILED
        && hasFalseResult


    if (isSuccess) {
        return ERunStatus.PASSED
    }

    if (isFailed) {
        return ERunStatus.FAILED
    }

    return status
}

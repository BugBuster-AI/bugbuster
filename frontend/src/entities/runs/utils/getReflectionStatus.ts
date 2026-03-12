import { EStatusIndicator } from '@Common/components';
import { getRunStatusToIndicator } from '@Common/utils/common';
import { ERunStatus } from '@Entities/runs/models';
import isNil from 'lodash/isNil';

export const getReflectionStatus = (reflection: ERunStatus | null | boolean): EStatusIndicator => {
    if (isNil(reflection)) {
        return EStatusIndicator.IDLE;
    }

    if (reflection === false) {
        return EStatusIndicator.ERROR
    }

    if (reflection === true) {
        return EStatusIndicator.SUCCESS
    }

    return getRunStatusToIndicator(reflection)
}


export const getReflectionRunStatus = (reflection?: ERunStatus | null | boolean): ERunStatus => {
    if (isNil(reflection)) {
        return ERunStatus.UNTESTED
    }

    if (reflection === false) {
        return ERunStatus.FAILED
    }

    if (reflection === true) {
        return ERunStatus.PASSED
    }

    return reflection
}

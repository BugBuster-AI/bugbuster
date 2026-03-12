import { ERunStatus } from '@Entities/runs/models';
import { ETestCaseType } from '@Entities/test-case/models';
import includes from 'lodash/includes';

export enum ECaseState {
    INITIAL = 'initial',
    MANUAL_EDIT = 'manual_edit',
    MANUAL_FINISH = 'manual_finish',
    AUTO_FINISH = 'auto_finish',
    AUTO_IN_PROGRESS = 'auto_in_progress',
    UNTESTED = 'untested'
}

// const FINISHED_STATUS = [ERunStatus.FAILED, ERunStatus.PASSED]
const IN_PROGRESS_STATUS = [ERunStatus.IN_PROGRESS, ERunStatus.IN_QUEUE, ERunStatus.RETEST, ERunStatus.STOP_IN_PROGRESS]

export const getCaseState = (type?: ETestCaseType, status?: ERunStatus): ECaseState => {
    let state: ECaseState = ECaseState.INITIAL

    if (status === ERunStatus.UNTESTED) {
        state = ECaseState.UNTESTED

        return state
    }

    switch (type) {
        case ETestCaseType.automated: {
            if (includes(IN_PROGRESS_STATUS, status)) {
                state = ECaseState.AUTO_IN_PROGRESS
            } else {
                state = ECaseState.AUTO_FINISH
            }

            break
        }

        case ETestCaseType.manual: {
            if (includes(IN_PROGRESS_STATUS, status)) {
                state = ECaseState.MANUAL_EDIT
            } else {
                state = ECaseState.MANUAL_FINISH
            }

            break
        }
    }

    return state
}

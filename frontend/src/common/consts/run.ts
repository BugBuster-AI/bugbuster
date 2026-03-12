import { ERunStatus, IRunById } from '@Entities/runs/models';
import { ETestCaseType } from '@Entities/test-case/models';

export const REFETCH_RUN_INTERVAL = 3000

export const NEED_REFETCH_STATUSES = [
    ERunStatus.UNTESTED,
    ERunStatus.IN_QUEUE,
    ERunStatus.PREPARATION,
    ERunStatus.STOP_IN_PROGRESS,
    ERunStatus.IN_PROGRESS
]
export const PROGRESS_STATUSES = [
    ERunStatus.IN_PROGRESS,
    ERunStatus.PREPARATION,
    ERunStatus.IN_QUEUE,
    ERunStatus.STOP_IN_PROGRESS,
]

export const SUCCESS_STATUSES = [
    ERunStatus.PASSED,
    ERunStatus.FAILED
]


export const needRefetchRun = (run?: IRunById | null) => {
    if (run?.case?.case_type_in_run === ETestCaseType.manual) {
        return false
    }

    return !run?.video?.url;
}

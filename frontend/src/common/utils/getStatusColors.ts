import { ERunStatus } from '@Entities/runs/models';

export const getStatusColors = (status: ERunStatus) => {
    switch (status) {
        case ERunStatus.IN_PROGRESS:
            return 'blue'
        case ERunStatus.PASSED:
            return 'green'
        case ERunStatus.FAILED:
            return 'red'
        case ERunStatus.UNTESTED:
            return 'default'
        case ERunStatus.RETEST:
            return 'cyan'
        case ERunStatus.SCHEDULED:
            return 'orange'
        case ERunStatus.BLOCKED:
            return 'orange'
        case ERunStatus.SKIPPED:
            return 'default'
        case ERunStatus.STOPPED:
            return 'default'
        case ERunStatus.IN_QUEUE:
            return 'blue'
        case ERunStatus.INVALID:
            return 'purple'
        case ERunStatus.AFTER_STEP_FAILURE:
            return 'orange'
        default:
            return 'default'
    }
}

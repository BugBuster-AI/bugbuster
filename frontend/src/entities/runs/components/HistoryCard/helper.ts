import { ERunStatus } from '@Entities/runs/models';
import { StepProps } from 'antd';

export const adaptStatus = (status: ERunStatus): StepProps['status'] => {
    switch (status) {
        case ERunStatus.IN_PROGRESS:
            return 'process';
        case ERunStatus.PASSED:
            return 'finish';
        case ERunStatus.FAILED:
            return 'error';
        default:
            return 'wait';
    }
}

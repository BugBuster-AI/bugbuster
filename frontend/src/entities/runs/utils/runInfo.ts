import { PROGRESS_STATUSES, SUCCESS_STATUSES } from '@Common/consts/run.ts';
import { IRunById } from '@Entities/runs/models';
import { ETestCaseType } from '@Entities/test-case/models';
import includes from 'lodash/includes';

export const getRunInfo = (run?: IRunById) => {
    if (!run) {
        return {}
    }

    const isAutomatedCase = run.case.case_type_in_run === ETestCaseType.automated
    const isInProgress = includes(PROGRESS_STATUSES, run?.status)
    const isGeneratingVideo = (!run?.video?.url && !isInProgress && includes(SUCCESS_STATUSES, run?.status))
        && isAutomatedCase
    const isInFinish = Boolean(!isInProgress && !isGeneratingVideo && run?.video?.url)
    const hasVideo = !!(run?.video?.url)

    return {
        isInFinish,
        isGeneratingVideo,
        isInProgress,
        hasVideo
    }
}

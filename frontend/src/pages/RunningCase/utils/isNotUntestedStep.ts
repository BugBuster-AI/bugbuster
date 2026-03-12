import { ERunStatus, IRunStep } from '@Entities/runs/models';

export const isNotUntestedStep = (step?: IRunStep) => {
    return step?.status_step !== ERunStatus.UNTESTED && !!step?.status_step
}

export const isNotUntestedLocalCreated = (step?: IRunStep) => {
    return step?.status_step !== ERunStatus.UNTESTED || 
    (step?.status_step === ERunStatus.UNTESTED && step?.isLocalCreated )
    && !!step?.status_step
}

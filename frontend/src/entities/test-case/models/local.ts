import { ERunStatus, IMedia, TStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';
import { ReactNode } from 'react';

export enum ELocalStepStatus {
    FAILED = 'failed',
    SUCCESS = 'success',
    UNTESTED = 'untested'
}

export interface ILocalStepData {
    type: EStepType
    partNum?: number
    partOriginal?: number // оригинальный индекс, без учета reflection result
    partAll?: number;
    status?: ELocalStepStatus
    completeTime?: string | number
    id?: string | number
    name?: string;
    description?: string | ReactNode;
    title?: string
    actionType?: string;
    beforeImage?: IMedia
    afterImage?: IMedia
    attachments?: IMedia[]
    group: string
    isLoading?: boolean
    extra?: IExtraCaseType
}

export interface ILocalRunData {
    steps: Record<TStepGroup, ILocalStepData[]>
    attachments?: IMedia[]
    status?: ERunStatus
}

export interface ITempTestCaseFormSettings {
    alreadyShowWarningContextScreenshots?: boolean
}

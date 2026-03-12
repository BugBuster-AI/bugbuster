import { EStatusIndicator } from '@Common/components';
import { IGetCoordinatesResponse } from '@Entities/common/models/get-coordinates.ts';
import { IRunById, IRunStep } from '@Entities/runs/models';

export interface IRunningStep extends Partial<IRunStep> {
    visible_name: string;
    status: EStatusIndicator;
    isLoading: boolean
    runIndex: number
}

export interface ICommittedGeneratedData extends IGetCoordinatesResponse {
}

export interface IChangedRun extends Omit<IRunById, 'steps'> {
    steps: IRunningStep[]
}

export interface ICommitedStep {
    name?: string;
    // Если отредоктирован
    isEdited?: boolean
    // Если редактируется в данный момент
    isEditing?: boolean
    generatedData?: ICommittedGeneratedData
    tempGeneratedData?: ICommittedGeneratedData
}

export interface ICommitedStepsData {
    [stepId: string]: ICommitedStep
}

export interface IEditingStep {
    id: string;
    step: IRunStep
}

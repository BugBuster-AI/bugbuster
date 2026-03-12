import { IStep } from '@Common/types';
import { ITestCase } from '@Entities/test-case/models';

export interface IFormStep extends IStep {

}

export interface IBaseForm extends Partial<Pick<ITestCase, 'case_id' | 'type' | 'environment_id'>> {
    priority: string;
    status: string
    url: string
    suite_id: string
    name: string
    executionType: string
    steps: IFormStep[]
    before_steps: IFormStep[]
    after_steps: IFormStep[]
    before_browser_start: IFormStep[]
}

export interface IBaseTestCasePayload extends Omit<IBaseForm, 'executionType'> {
}

export enum EMenuActions {
    CLONE_STEP = 'clone',
    DELETE_STEP = 'delete',
    ADD_STEP = 'add_step',
    ADD_RESULT = 'add_result',
    ADD_API = 'add_api',
    ADD_SHARED_STEP = 'add_shared_step',
}

export enum EMenuExpectedResultActions {
    SET_STATE_VERIF = 'set_state_verif',
    SET_DYNAMIC_CHANGE_VERIF = 'set_dynamic_change_verif'
}


// в кейсах
export enum EStepType {
    API = 'api',
    // важно - в ранах step === "step", в кейсах step === "action"
    STEP = 'action',
    RESULT = 'expected_result',
    SHARED_STEP = 'shared_step'
}

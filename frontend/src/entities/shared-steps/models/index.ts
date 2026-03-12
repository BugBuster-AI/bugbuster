import { ITestCaseStep } from '@Entities/test-case/models';

export interface ISharedStepListItem {
    id: string;
    name: string;
    description?: string;
    project_id: string;
    created_at: string;
    updated_at: string;
}

export interface IUpdateSharedStepPayload {
    name: string;
    description?: string;
    steps: ITestCaseStep[]
}

export * from './shared-steps'
export * from './get-list'
export * from './create.ts'
export * from './get-by-id.ts'

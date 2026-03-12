import { ITestCaseStep } from '@Entities/test-case/models';

export interface ISharedStep {
    name: string;
    description: string
    steps: ITestCaseStep[]
    is_valid: boolean
    validation_reason: Record<string, string>;
    action_plan: string
    shared_steps_id: string
    project_id: string
}

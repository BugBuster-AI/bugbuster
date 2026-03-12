import { ERunStatus, IMedia } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';

export interface ITestCaseListItem {
    case_id: string | number;
    name: string;
    type: ETestCaseType;
    position: number;
}

export enum ETestCaseType {
    automated = 'automated',
    manual = 'manual'
}

export enum ETestCasePriority {
    High = 'High',
    Medium = 'Medium',
    Low = 'Low'
}

export interface ITestCaseStep {
    type: EStepType
    value: string
    extra?: IExtraCaseType | null

    // Дополнительные поля (только для API шагов)
    method?: string;
    url?: string;
    headers?: Record<string, unknown>;
    data?: Record<string, unknown> | string;
    files?: Record<string, unknown>;
}

export interface ITestCase {
    attachments?: IMedia[]
    variables?: string
    description?: string
    name: string;
    original_case: Omit<ITestCase, 'original_case'>
    group_run_case_id?: string
    key?: string
    context: string | null;
    before_steps?: ITestCaseStep[]
    steps?: ITestCaseStep[]
    before_browser_start: ITestCaseStep[]
    after_steps: ITestCaseStep[]
    validation_steps: Record<string | number, string>[]
    validation_task: string;
    type: ETestCaseType; // Тип ('Automated')
    status: string // Статус ('Draft')
    url: string;
    is_valid: boolean;
    priority: string;
    validation_reason: Record<number, string>
    action_plan: IActionPlan[]
    external_id: string; // Внешний идентификатор
    case_id: string; // Идентификатор кейса
    suite_id: string; // Идентификатор сьюта
    position: number;
    case_type_in_run?: ETestCaseType
    actual_run_id?: string,
    environment_id?: string | null
    project_id?: string
    actual_status?: ERunStatus
}

export interface IActionPlan {
    action_type: string;
    element_type: string;
    element_name: string;
    positional_description: string | null;
    text_to_type: string | null;
    extra?: any
    key_to_press: string | null;
    scroll_element_name: string | null;
    wait_time: string | null;
    tab_name: string | null;
}

// legacy
export interface ITestCaseCreatePayload {
    name: string;
    context?: string;
    before_steps?: string[];
    steps?: string[];
    before_browser_start: string[]
    after_steps?: string[];
    validation_steps?: Record<number, string>[];
    validation_task?: string;
    type: string;
    status: string;
    priority: string;
    url: string;
    external_id?: string;
    suite_id: string;
    new_position?: number;
}

export interface ITestCaseCreateFromRecordPayload extends ITestCaseCreatePayload {
    happy_pass_id: string
}

export interface ITestCaseUpdatePayload extends Partial<ITestCaseCreatePayload> {
    case_id: string
}

export interface IStartCaseRun {
    run_id: string
}

export interface IChangeCasePosition {
    case_id: string;
    new_position: number;
}

export * from './local.ts'

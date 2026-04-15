import type { IResolution } from '@Entities/environment/models';
import { ERunStatus, IMedia } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';

export interface ITestCaseListItem {
    case_id: string | number;
    name: string;
    type: ETestCaseType;
    position: number;
    /** Playwright codegen (из user_tree / get_case_by_case_id) */
    codegen_regeneration_required?: boolean;
    can_run_playwright_js?: boolean;
    codegen_job_state?: string | null;
    /** Есть ли подходящий VLM-прогон для старта генерации кода */
    codegen_can_start_reference?: boolean;
    codegen_reference_block_reason?: string | null;
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

export type TExecutionEngine = 'vlm' | 'playwright_js'

export interface ICodegenEligibility {
    allowed: boolean
    reason_code?: string | null
}

export interface ICodegenJobError {
    message?: string
    step_uid?: string | null
    reason_code?: string
}

export interface ICodegenLogEntry {
    t?: string
    level?: string
    message?: string
    step_uid?: string | null
    phase?: string | null
    /** Presigned GET из backend (лог в MinIO) */
    screenshot_url?: string | null
    /** Legacy: inline base64 из старых записей Redis */
    screenshot_base64?: string | null
    screenshot_mime_type?: string | null
}

export interface ICodegenJobState {
    task_id?: string | null
    state?: string | null
    error?: ICodegenJobError | null
    run_id?: string | null
    log?: ICodegenLogEntry[]
    /** Per-step validation attempts cap chosen when the job was started */
    max_validation_attempts?: number | null
    /** ISO timestamp последнего обновления задачи в Redis (бэкенд) */
    updated_at?: string | null
}

export interface ICodegenStatusResponse {
    codegen_regeneration_required: boolean
    codegen_regeneration_since?: string | null
    codegen_first_requested_at?: string | null
    source_run_id?: string | null
    job: ICodegenJobState
    codegen_eligibility?: ICodegenEligibility
}

export interface ICodegenStepSpan {
    step_uid: string
    start_line: number
    end_line: number
}

export interface ICodegenArtifactResponse {
    source_code: string
    step_spans: ICodegenStepSpan[]
    source_run_id: string
    artifact_id: string
}

export interface ITestCaseStep {
    type: EStepType
    value: string
    step_uid?: string
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
    /**
     * Снимок окружения с бэкенда (например в `current_case_version`): разрешение viewport — `resolution`.
     */
    environment?: {
        environment_id?: string
        resolution?: IResolution
        title?: string
        browser?: string
        operation_system?: string
        project_id?: string
    } | null
    project_id?: string
    actual_status?: ERunStatus
    codegen_regeneration_required?: boolean
    codegen_regeneration_since?: string | null
    codegen_first_requested_at?: string | null
    can_run_playwright_js?: boolean
    codegen_job_state?: string | null
    codegen_job_updated_at?: string | null
    codegen_job_error_reason_code?: string | null
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
    execution_engine?: TExecutionEngine
}

export interface IChangeCasePosition {
    case_id: string;
    new_position: number;
}

export * from './local.ts'

import { IMedia } from '@Entities/runs/models';

export interface ITestCaseVariable {
    name: string;
    value: string;
    original: string;
    positions: [number, number][]
    key: string
}

export type SetVariables = Record<string, string>

export interface IValidationType {
    target: string;
    validation_type: string;
    expected_value: string
}

export interface IExtraCaseType {
    variables?: ITestCaseVariable[];
    set_variables?: SetVariables
    validations?: IValidationType[]

    // используется в проверках
    use_single_screenshot?: boolean

    // === start: только в ранах ===
    api_status_code?: number
    shared_step?: boolean
    shared_step_group_index?: number
    shared_step_group_size?: number
    shared_step_id?: string
    api_response?: string
    validations_log?: string[]
    value?: string
    variables_store?: SetVariables
    // контекстные скриншоты в степах
    context_screenshot_path?: IMedia | null
    context_screenshot_used?: boolean
    context_screenshot_log?: string
    // === end: только в ранах ===

    // в новом формате ранов, чтобы не парсить курл еще раз
    url?: string;
    method?: string
}

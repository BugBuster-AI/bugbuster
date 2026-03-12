import { IPaginationResponse, TStepsVariants } from '@Common/types';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ETestCaseType, ITestCase } from '@Entities/test-case/models';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';

// для получения полей из api
export enum EStepGroup {
    BEFORE_BROWSER = 'before_browser_start',
    BEFORE = 'before_steps',
    STEPS = 'steps',
    AFTER = 'after_steps'
}

export type TStepGroup = 'before' | 'step' | 'after' | 'before_browser'
export type TStepType = 'step' | 'expected'

export interface IRun {
    id: string
    name: string;
    date: string;
    streams: string
    // TODO: Поправить
    status: ERunStatus;
    deadline: string;
    author: string;
    time: number
    stats: IRunStats
    data: IGroupedRun
    parallel_exec?: number
    use_parallel_flag?: boolean
}

export interface IGetRunsPayload {
    suite_id?: string
    case_id?: string;
    created_at?: string
    start_date?: string
    end_date?: string;
    status?: string
    limit?: string
    offset?: string
}

export enum ECaseAction {
    CLICK = 'CLICK',
    SCROLL = 'SCROLL',
    INPUT = 'INPUT',
    WAIT = 'WAIT'
}

export interface IMedia {
    bucket: string;
    url: string;
    file: string
}

export interface IReflectionResult {
    /*
     * Only front
     * localId?: string
     */

    /** 
     * Не приходит с бэка, но продолжает юзаться при дебаг режиме
     */
    reflection_time?: string
        
    reflection_description?: string;
    reflection_result: ERunStatus | boolean
    reflection_title?: string
    reflection_step?: string
    attachments?: IMedia[]
    part_num?: number | string
    part_all?: number
    reflection_thoughts?: string
}

interface ICoordinates {
    x: number,
    y: number,
    width: number,
    height: number
}


export interface IRunStep {
    // *** only SINGLE RUN ***
    localId?: string // локальный id с зашифрованой информацией (stepGroup.index_step.reflectionIndex ?? false)
    localUUID?: string // локальный UUID для идентификации шага
    localIndexStep?: number // локальный индекс шага, который будет пересчитываться локаьлно
    isLocalCreated?: boolean // создан ли шаг локально
    /** Editing **/
    isLoading?: boolean // идет ли загрузка шага
    contextScreenshotMode?: { // режим контекстного скриншота (в одиночном ране)
        coordinates?: ICoordinates
        isEnabled?: boolean
        highlightColor?: string
        isNewCoordinates?: boolean
    }
    editingClickArea?: { // режим редактирования области клика (в одиночном ране)
        highlightColor?: string;
        isThinkingMode?: boolean;
        isLoading?: boolean;
        hasResponse?: boolean;
        error?: string;
        coordinates?: ICoordinates;
    }
    checkResults?: { // результаты проверки шага (после нажатия на Check в одиночном ране)
        status: ERunStatus,
        title?: string,
        description: string
        time?: string;
    }
    error?: string // ошибка при загрузке/сохранении шага
    errorType?: string // тип ошибки 
    isEdited?: boolean // был ли отредактирован шаг
    // *****

    status_task?: string;
    status_step: ERunStatus
    reflection_steps: { instruction: string, use_single_screenshot: boolean }[]
    comment?: string;
    attachments?: IMedia[]
    is_test_successful?: boolean,
    extra?: IExtraCaseType | null
    /*
     * TOOD: old
     * reflection_results: null | IReflectionResult[],
     */
    validation_result?: null | IReflectionResult
    reflection_title: null | string,
    part_num: number,
    part_all: number,
    step_group: TStepGroup
    original_step_description: string
    raw_step_description: string
    index_step: number
    step_type: EStepType
    model_time: string // seconds,
    step_time: string // seconds,
    step_description: string,
    action: string,
    coords: number[],
    text: string;
    before_annotated_url: IMedia,
    before: IMedia,
    after: IMedia
}

export interface IRunById {
    run_id: string;
    case: ITestCase,
    status: ERunStatus,
    step_group: TStepsVariants
    attachments?: IMedia[],
    run_summary: null | string
    created_at: string;
    start_dt: string;
    end_dt: string;
    complete_time: string // seconds,
    video?: IMedia,
    steps: IRunStep[]
    logs?: string;
    trace?: string;
    show_trace?: string
}

export interface IRunList extends IPaginationResponse {
    items: IRunById[]
}

// Статусы ранов
export enum ERunStatus {
    UNTESTED = 'untested',
    PASSED = 'passed',
    FAILED = 'failed',
    BLOCKED = 'blocked',
    INVALID = 'invalid',
    RETEST = 'retest',
    IN_PROGRESS = 'in_progress',
    IN_QUEUE = 'in_queue',
    PREPARATION = 'preparation',
    SKIPPED = 'skipped',
    // TODO: Уточнить по этим статусам
    SCHEDULED = 'scheduled',
    STOPPED = 'stopped',
    STOP_IN_PROGRESS = 'stop_in_progress',
    AFTER_STEP_FAILURE = 'after_step_failure'
}

export enum EStepStatus {
    FAILED = 'failed',
    SUCCESS = 'passed'
}

/****** Групповые раны ******/

// Параметры для запроса групповых ранов
export interface IGroupedRunsParams {
    group_run_id?: string;
    project_id?: string;
    status?: string[],
    limit?: number;
    search?: string;
    order_direction?: 'asc' | 'desc'
    order_by?: string
    offset?: number
    filter_cases?: string
}

export interface IGroupRunList extends IPaginationResponse {
    items: IGroupedRun[]
}

export interface IRunStats {
    untested: number,
    passed: number,
    failed: number,
    blocked: number,
    invalid: number,
    retest: number,
    in_progress: number,
    in_queue: number,
    stopped: number,
    stop_in_progress: number,
    preparation: number,
    after_step_failure: number
}

// Групповые раны
export interface IGroupedRun {
    group_run_id: string;
    variables?: string;
    user_id: string;
    created_at: string;
    name: string;
    description: string;
    status: ERunStatus;
    environment: string; // id environment
    deadline: string;
    use_parallel_flag?: boolean
    parallel_exec: number;
    host: string;
    /** @deprecated используй parallel */
    suites?: ISuiteInGroupedRun[]
    /** Дерево параллельных кейсов */
    parallel: ISuiteInGroupedRun[]
    /** Плоский список последовательных кейсов */
    sequential: ISequentialRunCase[]
    stats: IRunStats
    complete_time: string | null
}

// Кейсы в групповых ранах
export interface ITestCaseInGroupedRun extends ITestCase {
    position: number;
    actual_status: ERunStatus;
    actual_run_id: string
    group_run_case_id: string;
    actual_complete_time: string | null
    actual_start_dt: string | null
    actual_end_dt: string | null
    case_type_in_run?: ETestCaseType
    execution_mode?: string
    execution_order?: number | null
}

// Кейс в sequential-секции группового рана
export interface ISequentialRunCase {
    group_run_case_id: string;
    case_id: string;
    execution_mode: 'sequential';
    execution_order: number;
    suite_path: string;
    case: ITestCaseInGroupedRun;
}

// Сьюты в групповых ранах
export interface ISuiteInGroupedRun {
    suite_id: string;
    suite_name: string;
    cases: ITestCaseInGroupedRun[]
    suite_description?: string
    children: ISuiteInGroupedRun[]
    stats: IRunStats
    complete_time: string | null
}

// Ответ при запуске групповых ранов
export interface IStartGroupedRunResponse {
    run_ids: string[]
}

// Ответ при остановке групповых ранов
export interface IStopGroupedRunResponse {
    stopped_run_ids: string[]
}

export interface IRunCase {
    case_id: string;
    execution_mode: 'sequential' | 'parallel';
    execution_order: number | null;
}

// Пэйлоад для создания групповых ранов
export interface ICreateGroupedRunPayload {
    name: string;
    project_id: string
    description: string;
    environment_id: string;
    deadline: string;
    parallel_exec?: number;
    host: string;
    cases: IRunCase[]
}

export interface ICreateGroupedRunResponse {
    group_run_id: string
    user_id: string
    created_at: string
    name: string
    description: string
    status: ERunStatus
}


// Удаление кейсов из группового рана
export interface IDeleteCasesFromGroup {
    runId: string;
    case_ids: string[]
}


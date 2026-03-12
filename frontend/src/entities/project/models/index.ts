export interface IProjectListItem {
    project_id: string;
    name: string;
    description: string;
    suite_count: number;
    case_count: number;
    run_count: number
    parallel_exec?: number
}

export interface ICreateProjectPayload {
    name: string;
    description: string
    parallel_exec?: number
}

export interface IProjectWithId extends ICreateProjectPayload {
    project_id: string
}

export interface IGetProjectListPayload {
    search?: string
}

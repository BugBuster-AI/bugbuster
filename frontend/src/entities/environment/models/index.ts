export interface IResolution {
    width: number;
    height: number;
}

export interface IEnvironmentListItem {
    title: string;
    description?: string | null;
    browser: string;
    operation_system: string;
    resolution: IResolution
    environment_id: string;
    project_id: string;
    retry_enabled?: boolean;
    retry_timeout?: number;
}

export interface ICreateEnvironmentPayload extends Omit<IEnvironmentListItem, 'environment_id'> {
}

export interface IUpdateEnvironmentPayload extends Omit<IEnvironmentListItem, 'environment_id' | 'project_id'> {
}

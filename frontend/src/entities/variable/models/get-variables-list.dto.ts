import { IVariable } from '@Entities/variable/models/interfaces.ts';

export interface IGetVariablesListRequest {
    variables_kit_id: string
    search?: string
}

export interface IGetVariableListResponse {
    variables_count: number;
    variables_details: IVariable[]
}

export interface IGetVariablesListByNameRequest {
    variables_kit_name: string
    project_id: string
}

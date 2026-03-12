import { IVariable } from '@Entities/variable/models/interfaces.ts';

export interface IGetVariableRequest {
    variable_details_id: string
}

export interface IGetVariableResponse extends IVariable {
}

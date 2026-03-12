import { IVariable } from '@Entities/variable/models/interfaces.ts';

export interface ICreateVariableRequest extends Omit<IVariable, 'variable_details_id' | 'computed_value'> {
}

export interface ICreateVariableResponse extends IVariable {
}

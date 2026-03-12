import { IVariable } from '@Entities/variable/models/interfaces.ts';

export interface IUpdateVariableRequest extends Omit<IVariable, 'variables_kit_id'> {

}

export interface IUpdateVariableResponse extends IVariable {
}

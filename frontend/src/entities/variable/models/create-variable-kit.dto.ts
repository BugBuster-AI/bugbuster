import { IVariableKit } from '@Entities/variable/models/interfaces.ts';

export interface ICreateVariableKitRequest extends Omit<IVariableKit, 'variables_kit_id'> {

}

export interface ICreateVariableKitResponse extends IVariableKit {
    variables_kit_name: string;
    variables_kit_description: string;
    variables_kit_id: string;
    project_id: string;
}

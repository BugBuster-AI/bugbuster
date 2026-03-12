import { IVariableKit } from '@Entities/variable/models/interfaces.ts';

export interface IGetKitVariableByIdRequest extends Pick<IVariableKit, 'variables_kit_id'> {
    variables_kit_id: string
}

export interface IGetKitVariableByIdResponse extends IVariableKit {
}

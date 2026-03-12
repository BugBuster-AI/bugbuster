import { IVariableKit } from '@Entities/variable/models';

export interface IUpdateVariableKitRequest extends Partial<Omit<IVariableKit, 'project_id'>> {

}

export interface IUpdateVariableKitResponse extends IVariableKit {
}

import { ICurlObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';

export interface IVariableEdit {
    name: string
    path: string;
}

export interface IHeaderEdit {
    key: string;
    value: string | null;
}

export interface IParamEdit extends IDataObject {
}

export interface IDataObject {
    key: string;
    value: string
}

export interface IFormDataItem extends IDataObject {
    type: 'text' | 'file'
}

export interface IValidationEdit {
    target: string;
    type: string;
    expectedValue: string
}

export interface IInitialData {
    curlString: string;
    curlObj: ICurlObject
    extra: IExtraCaseType | null
}

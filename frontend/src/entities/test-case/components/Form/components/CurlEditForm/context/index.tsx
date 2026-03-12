import { createContext, useContext } from 'react';
import {
    IDataObject, IFormDataItem,
    IHeaderEdit, IInitialData, IParamEdit,
    IValidationEdit,
    IVariableEdit
} from '../models.ts';

export type TBodyType = 'urlEncoded' | 'formData' | 'raw' | 'none'
export type TBodyRawType = 'json' | 'text' | 'xml' | 'html' | 'javascript'

export interface IBodyState {
    formData?: IFormDataItem[]
    urlEncoded?: IDataObject[]
    raw?: {
        type?: TBodyRawType
        value?: string
    },
    currentBodyType: TBodyType
}

// make temp state ?
export interface IFormState {
    params: IParamEdit[]
    headers: IHeaderEdit[]
    validation: IValidationEdit[]
    variables: IVariableEdit[]
    body: IBodyState
    url: string
    method: string
}

interface ICurlEditFormContext {
    formData: IFormState
    sourceData?: IInitialData
    activeTab: string

    setActiveTab: (tab: string) => void
    setUrl: (value: string) => void
    setBody: (body: Partial<IBodyState>) => void
    setParams: (params: IParamEdit[]) => void
    setHeaders: (headers: IHeaderEdit[]) => void
    setValidation: (validation: IValidationEdit[]) => void
    setVariables: (variables: IVariableEdit[]) => void
}

export const CurlEditFormContext = createContext<ICurlEditFormContext | undefined>(undefined)

export const useCurlEditFormContext = () => {
    const context = useContext(CurlEditFormContext)

    if (!context) {
        throw new Error('useCurlEditFormContext must be used within a CurlEditFormContextProvider')
    }

    return context
}

export * from './selectors.ts'

import { IStep } from '@Common/types';
import { ICurlObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';
import { createContext, useContext } from 'react';


interface IApiInputContext {
    curlString: string;
    curlObj: ICurlObject;
    originCurlString: string

    extra?: IExtraCaseType | null
    // данные степа
    stepData: IStep

    setStepData: (data: IStep) => void
    setExtra: (data: Partial<IExtraCaseType>) => void
    setCurlString: (curl: string) => void
    setCurlObj: (curl: {}) => void
    setOriginCurlString: (curl: string) => void
}

export const ApiInputContext = createContext<IApiInputContext | undefined>(undefined)

export const useApiInputContext = () => {
    const context = useContext(ApiInputContext)

    if (!context) {
        throw new Error('useApiInputContext must be used within a ApiInputContextProvider')
    }

    return context
}

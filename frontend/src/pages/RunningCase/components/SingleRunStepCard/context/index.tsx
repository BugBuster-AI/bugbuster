import { IGetCoordinatesResponse } from '@Entities/common/models/get-coordinates.ts';
import { IRunStep } from '@Entities/runs/models';
import { createContext, Dispatch, SetStateAction, useContext } from 'react';

interface IContext {
    isEditing: boolean
    changeEditing: (val: boolean) => void
    isEditable: boolean
    stepItem: IRunStep

    tempValue?: string;
    tempGeneratedData?: IGetCoordinatesResponse
    loading?: boolean
    stepId?: string
    useSingleScreenshot?: boolean
    setUseSingleScreenshot: (val: boolean) => void

    setTempGeneratedData: Dispatch<SetStateAction<IGetCoordinatesResponse | undefined>>
    setTempValue: Dispatch<SetStateAction<string | undefined>>
    setLoading: Dispatch<SetStateAction<boolean>>
}

export const SingleRunStepContext = createContext<IContext | undefined>(undefined)

export const useSingleRunStepContext = () => {
    const context = useContext(SingleRunStepContext)

    if (!context) {
        throw new Error('Component must be in SingleRunStepContextProvider')
    }

    return context
}

import { createContext, useContext } from 'react';

export interface IMovingCase {
    suite_id: string;
    case_id: string
}

interface ISuitesControl {
    movingCaseToSuite?: IMovingCase

    setMovingCaseToSuite: (data?: IMovingCase) => void
}

export const SuitesControlContext = createContext<ISuitesControl | undefined>(undefined)

export const useSuitesControlContext = () => {
    const context = useContext(SuitesControlContext)

    if (!context) {
        throw new Error('Erro: using SuitesControl outside Provider')
    }

    return context
}

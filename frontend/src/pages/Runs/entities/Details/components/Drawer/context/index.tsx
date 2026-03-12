import { ECaseState } from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils';
import { createContext, useContext } from 'react';


export interface IDrawerContext {
    currentCaseType: ECaseState
    isLoading: boolean
    setLoading: (value: boolean) => void
    setCurrentCaseType: (value: ECaseState) => void
}

export const GroupCaseDrawerContext = createContext<IDrawerContext | undefined>(undefined)

export const useGroupDrawerContext = () => {
    const context = useContext(GroupCaseDrawerContext)

    if (!context) {
        throw new Error('useContext using outside GroupCaseDrawerContext.Provider')
    }

    return context
}


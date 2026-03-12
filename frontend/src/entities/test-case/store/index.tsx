import { createSelectors } from '@Common/lib';
import { ITestCase } from '@Entities/test-case/models';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

interface IState {
    currentCase?: ITestCase
    drawerOpen: boolean
    activeDrawerKey: string
}

interface IAction {
    clickDrawer: (value: boolean) => void
    setCurrentCase: (data?: ITestCase) => void
    updateCurrentCase: (data?: Partial<ITestCase>) => void
    setActiveDrawerKey: (key: string) => void
}

type TTestCaseStore = IState & IAction

const initialState: IState = {
    currentCase: undefined,
    drawerOpen: false,
    activeDrawerKey: '1'
}

const testCaseSlice: StateCreator<TTestCaseStore> = (set, get) => ({
    ...initialState,

    clickDrawer: (value) => {
        set({ drawerOpen: value })
    },
    setCurrentCase: (data) => {
        set({ currentCase: data })
    },

    setActiveDrawerKey: (key) => {
        set({ activeDrawerKey: key })
    },

    updateCurrentCase: (data) => {
        const prev = get().currentCase

        if (data && prev) {
            set({ currentCase: { ...prev, ...data } })
        }
    }
})

const withDevtools = devtools(testCaseSlice, { name: 'Test-case Store' })
const store = create(withDevtools)

export const useTestCaseStore = createSelectors(store)

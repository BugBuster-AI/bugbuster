import { createSelectors } from '@Common/lib';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

interface IState {
    searchValue?: string
}

interface IAction {
    setSearchValue: (value?: string) => void
}

type RecordsStore = IState & IAction

const initialState: IState = {
    searchValue: undefined
}

export const slice: StateCreator<RecordsStore, [['zustand/devtools', never]], []> = (set) => ({
    ...initialState,

    setSearchValue: (value) => {
        set({ searchValue: value })
    }
})

const withDevtools = devtools(slice, { name: 'Records-Store' })
const store = create(withDevtools)

export const useRecordsStore = createSelectors(store)

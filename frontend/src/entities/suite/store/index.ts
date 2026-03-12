import { createSelectors } from '@Common/lib';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';
import { ISuite } from '../models';

interface IState {
    selectedSuite: ISuite | null
    searchValue?: string
    loading: boolean

    hoveredSuiteId?: string
}

interface IAction {
    setSuite: (data: ISuite | null) => void;
    setSearchValue: (value?: string) => void
    setLoading: (loading: boolean) => void;

    setHoveredSuiteId: (id?: string) => void
}

const initialState: IState = {
    selectedSuite: null,
    loading: false,
    hoveredSuiteId: undefined
};

type TSuiteSlice = IState & IAction;

const suiteSlice: StateCreator<
    TSuiteSlice,
    [['zustand/devtools', never]],
    []
> = (set) => ({
    ...initialState,

    setHoveredSuiteId: (id) => set({ hoveredSuiteId: id }),
    setSearchValue: (searchValue) => set({ searchValue }),
    setLoading: (loading) => set({ loading }),
    setSuite: (data) => set({ selectedSuite: data }),
})

const withDevtools = devtools(suiteSlice, { name: 'Suite Store' })

const store = create(withDevtools)

export const useSuiteStore = createSelectors(store)




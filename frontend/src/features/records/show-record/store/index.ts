import { createSelectors } from '@Common/lib';
import { IFullHappyPastListItem } from '@Entities/records/models';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

export interface IState {
    record?: IFullHappyPastListItem
    currentImage?: number
    loading?: boolean
    error?: string
    open?: boolean
}

export interface IAction {
    setRecord: (record?: IFullHappyPastListItem) => void
    setCurrentImage: (currentImage: number) => void
    setLoading: (loading: boolean) => void
    setError: (error?: string) => void
    clear: () => void
    setOpen: (value: boolean) => void
}

type TShowRecordStore = IState & IAction

const initialState: IState = {
    record: undefined,
    currentImage: 0,
    loading: false,
    error: undefined,
    open: false,
}

const slice: StateCreator<TShowRecordStore, [['zustand/devtools', never]], []> = (set) => ({
    ...initialState,

    setLoading: (loading) => set({ loading }),
    setError: (error) => set({ error }),
    setRecord: (record) => set({ record }),
    setCurrentImage: (currentImage) => set({ currentImage }),
    setOpen: (open) => set({ open }),
    clear: () => set({ ...initialState })
})

const withDevtools = devtools(slice, { name: 'Show Record Store' })
const store = create(withDevtools)

export const useShowRecordStore = createSelectors(store)


import { createSelectors } from '@Common/lib';
import { IStreamsStatList, IStreamStat } from '@Entities/stream/models';
import get from 'lodash/get';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

interface IState {
    loading?: boolean;
    error?: string
    streams?: IStreamsStatList
    currentProjectStreams?: IStreamStat
}

interface IActions {
    setStreams: (data?: IStreamsStatList, loading?: boolean, error?: string, projectId?: string) => void
}

type TStreamStore = IState & IActions

const initialState: IState = {
    loading: false,
    error: undefined,
    streams: undefined
}

const streamSlice: StateCreator<TStreamStore> = (set) => ({
    ...initialState,

    setStreams: async (streams, loading, error, projectId) => {
        const currentProjectStreams = projectId
            ? get(streams?.project_statistics, projectId, undefined)
            : undefined

        if (currentProjectStreams) {
            set({ currentProjectStreams })
        }

        set({
            loading,
            error,
            streams,
        })
    }
})

const withDevtools = devtools(streamSlice, { name: 'Streams Store' })
const store = create(withDevtools)

export const useStreamStore = createSelectors(store)

import { createSelectors } from '@Common/lib';
import { IWorkspaceLimit, IWorkspaceListItem } from '@Entities/workspace/models';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

interface IState {
    workspace: IWorkspaceListItem | null
    limits: IWorkspaceLimit[],
}

interface IActions {
    setWorkspace: (project: IWorkspaceListItem) => void
    setLimits: (limits: IWorkspaceLimit[]) => void
}

type WorkspacesStore = IState & IActions

export const workspaceSlice: StateCreator<WorkspacesStore> = (set) => ({
    workspace: null,
    limits: [],

    setLimits: (limits) => set(() => ({ limits })),
    setWorkspace: (workspace) => set(() => ({ workspace }))
})

const withDevtools = devtools(workspaceSlice, { name: 'Workspace Store' })
const store = create(withDevtools)

export const useWorkspaceStore = createSelectors(store)

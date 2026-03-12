import { createSelectors } from '@Common/lib';
import { IProjectListItem } from '@Entities/project';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

interface IState {
    currentProject: IProjectListItem | null
}

interface IActions {
    setProject: (project?: IProjectListItem) => void
}

type ProjectStore = IState & IActions

export const projectSlice: StateCreator<ProjectStore> = (set) => ({
    currentProject: null,

    setProject: (project) => set(() => ({ currentProject: project }))
})

const withDevtools = devtools(projectSlice, { name: 'Project Store' })
const store = create(withDevtools)

export const useProjectStore = createSelectors(store)

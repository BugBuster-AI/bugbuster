import { createSelectors } from '@Common/lib';
import { IRun } from '@Entities/runs/models';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { ISuite } from '@Entities/suite/models';
import { ITestCase } from '@Entities/test-case/models';
import isNil from 'lodash/isNil';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

export type TCaseExecutionMode = EExecutionMode

export interface ICaseWithExecution {
    id: string
    executionMode: EExecutionMode
    executionOrder?: number
    caseData: ITestCase
}

type TSelectedCase = Record<string, ICaseWithExecution[]>

interface IState {
    selectedCaseId: TSelectedCase
    selectedSuiteId: string[]

    tempCases: TSelectedCase
    tempSuites: string[]

    currentSuite?: ISuite

    initialData?: IRun
    step?: 1 | 2
    isEdit?: boolean
    
    currentExecutionMode: EExecutionMode

    maxParallelThreads?: number
    selectedParallelThreads: number
}

interface IAction {
    setCaseId: (caseIds: TSelectedCase) => void
    setSuiteId: (suiteIds: string[]) => void
    setInitialData: (data?: IRun) => void
    
    setExecutionMode: (mode: EExecutionMode) => void

    setTempCases: (caseIds: TSelectedCase | undefined) => void
    setTempSuites: (suiteIds: string[]) => void
    setStep: (step: 1 | 2 | undefined) => void

    setCurrentSuite: (suite?: ISuite) => void
    saveTempValues: () => void

    setIsEdit: () => void
    
    setMaxParallelThreads: (threads?: number) => void
    setSelectedParallelThreads: (threads: number) => void

    clear: () => void
}

type TStore = IState & IAction

const initialValues: IState = {
    selectedSuiteId: [],
    selectedCaseId: {},
    step: undefined,
    tempCases: {},
    tempSuites: [],
    initialData: undefined,
    currentSuite: undefined,
    isEdit: false,
    maxParallelThreads: undefined,
    selectedParallelThreads: 1,
    currentExecutionMode: EExecutionMode.PARALLEL
}

const slice: StateCreator<TStore, [['zustand/devtools', never]], []> = (set, get) => ({
    ...initialValues,

    setExecutionMode: (mode) => {
        set({ currentExecutionMode: mode })
    },

    setInitialData: (data) => {
        set({
            initialData: data,
            selectedParallelThreads: data?.parallel_exec || 1
        })
    },

    setIsEdit: () => {
        set({ isEdit: true })
    },
    
    saveTempValues: () => {
        const tempCases = get().tempCases
        const tempSuites = get().tempSuites

        set({ selectedCaseId: tempCases, selectedSuiteId: tempSuites })
    },
    setTempCases: (caseIds) => {
        if (isNil(caseIds)) {
            set({ tempCases: {} })

            return
        }
        const prev = get().tempCases


        set({ tempCases: { ...prev, ...caseIds } })
    },
    setTempSuites: (suites) => {
        set({ tempSuites: suites })
    },
    setStep: (step) => {
        set({ step })
    },

    setSuiteId: (ids) => {
        set({ selectedSuiteId: ids })
    },

    setCurrentSuite: (suite) => {
        if (isNil(suite)) {
            set({ currentSuite: undefined })

            return
        }
        set({ currentSuite: suite })
    },

    setCaseId: (ids) => {
        set({ selectedCaseId: ids })
    },

    setMaxParallelThreads: (threads) => {
        set({ maxParallelThreads: threads })
    },

    setSelectedParallelThreads: (threads) => {
        set({ selectedParallelThreads: threads })
    },

    clear: () => {
        set(initialValues)
    }
})

const withDevtools = devtools(slice, { name: 'Create Run From Cases' })
const store = create(withDevtools)

export const useCreateRunStore = createSelectors(store)

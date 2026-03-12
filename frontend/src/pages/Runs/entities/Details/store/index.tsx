import { PAGINATION } from '@Common/consts';
import { createSelectors } from '@Common/lib';
import { IGroupedRun, IGroupRunList, ISuiteInGroupedRun } from '@Entities/runs/models';
import { IStreamStat } from '@Entities/stream/models';
import { useTestCaseStore } from '@Entities/test-case';
import { ITestCase } from '@Entities/test-case/models';
import { findCaseById } from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils/find-case.ts';
import { getFlatSuites } from '@Pages/Runs/entities/Details/utils/getFlatSuites.ts';
import filter from 'lodash/filter';
import head from 'lodash/head';
import includes from 'lodash/includes';
import isEmpty from 'lodash/isEmpty';
import isNil from 'lodash/isNil';
import trim from 'lodash/trim';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';


type TSelectedCase = Record<string, ITestCase[]>

interface IState {
    filters: string[]
    search?: string;
    data?: IGroupRunList
    isLoading?: boolean
    isError?: boolean
    runItem?: IGroupedRun
    currentCaseSuite?: ISuiteInGroupedRun
    openedCaseId?: string
    flatSuites: Record<string, ITestCase[]>
    streams: IStreamStat | null
    error?: string

    /* Если в данный момент запущен автоматический кейс в ретесте */
    isCaseFetching?: boolean

    selectedCases?: TSelectedCase

    /** Открыт ли drawer кейса */
    isDrawerOpen: boolean

    pagination: {
        page: number,
        pageSize: number
        total: number
    }
}

interface IAction {
    setFilter: (filter: string) => void
    clearFilters: () => void
    setSearch: (value: string) => void
    setData: (data: IGroupRunList) => void
    setOpenedCaseId: (id?: string) => void
    setCaseFetching: (value: boolean) => void
    updateFilters: (filters: string[]) => void
    setLoading: (value: boolean) => void
    setError: (value: boolean) => void
    setErrorMessage: (value?: string) => void

    setStreams: (data: IStreamStat | null) => void
    setFlatSuites: (data: Record<string, ITestCase[]>) => void

    setSelectedCase: (cases: TSelectedCase | undefined) => void

    updateCurrentCase: (id: string) => void
    setPagination: ({ page, pageSize }: { page?: number, pageSize?: number }) => void

    setCurrentCaseSuite: (suite: ISuiteInGroupedRun) => void
    setDrawerOpen: (value: boolean) => void
    clear: () => void
}

type TSlice = IState & IAction

const initialState: IState = {
    filters: [],
    runItem: undefined,
    streams: null,
    search: undefined,
    openedCaseId: undefined,
    data: undefined,
    currentCaseSuite: undefined,
    isCaseFetching: false,
    flatSuites: {},
    error: undefined,
    isDrawerOpen: false,

    selectedCases: {},

    pagination: {
        page: PAGINATION.PAGE,
        pageSize: PAGINATION.PAGE_SIZE,
        total: 0
    }
}

const slice: StateCreator<TSlice, [['zustand/devtools', never]], []> = (set, get) => ({
    ...initialState,

    setSearch: (search) => {
        if (!search) {
            set({ search: undefined })

            return
        }
        set({ search: trim(search) })
    },
    setErrorMessage: (message) => {
        set({ error: message })
    },
    setStreams: (streams) => {
        set({ streams })
    },

    setFlatSuites: (data) => {
        set({ flatSuites: data })
    },

    setOpenedCaseId: (id) => {
        set({ openedCaseId: id })
    },

    setCurrentCaseSuite: (suite) => {

        set({ currentCaseSuite: suite })
    },

    setDrawerOpen: (value) => {
        set({ isDrawerOpen: value })
    },

    setCaseFetching: (value) => {
        set({ isCaseFetching: value })
    },
    updateCurrentCase: (id: string) => {
        const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)
        const suites = get().runItem?.parallel
        const findCase = findCaseById(suites, id)

        if (findCase) {
            setCurrentCase(findCase)
        }
    },

    setData: (data) => {
        if (data) {
            const runItem = head(data.items);

            const f = getFlatSuites(runItem?.parallel);

            set({
                runItem,
                data,
                flatSuites: f
            });
        }
    },

    setSelectedCase: (caseIds) => {
        if (isNil(caseIds)) {
            set({ selectedCases: {} })

            return
        }
        const prev = get().selectedCases

        const updatedCases = { ...prev, ...caseIds };

        Object.keys(caseIds).forEach((key) => {
            if (isEmpty(caseIds[key])) {
                delete updatedCases[key];
            }
        });

        set({ selectedCases: updatedCases });
    },
    setLoading: (value) => set({ isLoading: value }),
    setError: (value) => set({ isError: value }),
    setFilter: (value) => {
        const prevFilters = get().filters
        const hasFilter = includes(prevFilters, value)
        const newFilters = !hasFilter ? [...prevFilters, value] : filter(prevFilters, (item) => item !== value)

        set({ filters: newFilters })
    },

    updateFilters: (filters) => {
        set({ filters })
    },

    clearFilters: () => {
        set({ filters: [] })
    },

    setPagination: ({ page, pageSize }) => {
        const prevPagination = get().pagination

        if (page) {
            set({
                pagination: {
                    ...prevPagination,
                    page: page,
                }
            })
        }

        if (pageSize) {
            set({
                pagination: {
                    ...prevPagination,
                    pageSize: pageSize,
                }
            })
        }
    },

    clear: () => {
        set(initialState)
    }
})

const withDevtools = devtools(slice, { name: 'Grouped_Run-Store' })
const store = create(withDevtools)

export const useGroupedRunStore = createSelectors(store)

import { createSelectors } from '@Common/lib';
import { deepMerge } from '@Common/utils/deepMerge';
import { IRunById, IRunStep } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IEditingStep } from '@Pages/RunningCase/store/models.ts';
import find from 'lodash/find';
import isArray from 'lodash/isArray';
import isBoolean from 'lodash/isBoolean';
import map from 'lodash/map';
import reject from 'lodash/reject';
import size from 'lodash/size';
import { devtools } from 'zustand/middleware';
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';
import { getStepId } from '../utils';
import { createEmptyStep } from './helper';

interface IState {
    selectedEditingStep?: IEditingStep
    // Оригинальный ран
    originRun?: IRunById
    // Рефетчатся ли степы
    isRefetchingSteps?: boolean
    // Рефетчится ли видео
    isRefetchingVideo?: boolean
    // Текущий ран
    currentRun?: IRunById

    // был ли отредактирован ран
    isEdited?: boolean

    selectedStep?: {
        id: string,
        step: Partial<IRunStep>
        clicked?: boolean
    }

    isLoading?: boolean
    isGlobalLoader?: boolean
    error?: string | boolean
    inProgress?: boolean
    // Готовые логи с информацией по каждому степу
    logs: IRunStep[]

    // Текущий редактируемый степ
    editingSteps: IEditingStep[]

    // сохраненный список переменных
    variablesList: Record<string, string>
}

interface IAction {
    setCurrentRun: (run: IRunById) => void
    setOriginRun: (run: IRunById) => void
    updateCurrentRun: (run: Partial<IRunById>) => void
    setIsEdited: (val: boolean) => void
    setSelectedEditingStep: (step: IEditingStep) => void
    setGlobalLoader: (isGlobalLoader: boolean) => void

    setRefetchingState: ({ steps, video }: { steps?: boolean, video?: boolean }) => void
    setSelectedStep: (id: string, step: Partial<IRunStep>, clicked?: boolean) => void
    setIsLoading: (isLoading: boolean) => void
    setError: (error?: string | boolean) => void
    setInProgress: (inProgress: boolean) => void
    clearStore: () => void

    setEditingStep: (step?: IEditingStep | IEditingStep[]) => void
    removeEditingStep: (stepUUID: string) => void

    updateEditingStep: (stepUUID: string, step: Partial<IRunStep>) => void
    setVariablesList: (variables?: Record<string, string>) => void
    
    // вставить шаг в ран
    insertStepAfter: (stepUUID: string, stepType: string) => void
    // удалить шаг из рана
    removeStepFromRun: (stepUUID: string) => void
}

type TRunningStore = IState & IAction

const initialState: IState = {
    selectedEditingStep: undefined,
    originRun: undefined,
    currentRun: undefined,
    isGlobalLoader: false,
    selectedStep: undefined,
    error: undefined,
    isLoading: false,
    inProgress: false,
    isRefetchingSteps: false,
    isRefetchingVideo: false,
    isEdited: false,

    editingSteps: [],
    logs: [],
    variablesList: {}
}

const slice: StateCreator<TRunningStore, [['zustand/devtools', never]], []> = (set, get) => ({
    ...initialState,

    insertStepAfter: (stepUUID, stepType) => {
        const currentRun = get().currentRun
        const currentSteps = currentRun?.steps || []

        if (!size(currentSteps)) {
            return
        }

        // Находим позицию текущего шага в массиве по UUID
        const currentStepArrayIndex = currentSteps.findIndex((step) => step.localUUID === stepUUID)
        
        if (currentStepArrayIndex === -1) {
            return
        }

        const currentStep = currentSteps[currentStepArrayIndex]

        if (!currentStep.step_group) {
            return
        }

        // Вычисляем новый индекс - вставляем ПОСЛЕ текущего шага
        const insertPosition = currentStepArrayIndex + 1
        const newStepIndex = currentStep.localIndexStep! + 1
        const newTotalSteps = currentSteps.length + 1
        
        const newStepId = getStepId({
            index: newStepIndex,
            group: currentStep.step_group
        })

        // Создаем пустой шаг через helper
        const newStep = createEmptyStep({
            stepId: newStepId,
            index: newStepIndex,
            partNum: insertPosition + 1, // Используем позицию в массиве, а не localIndexStep
            partAll: newTotalSteps,
            stepGroup: currentStep.step_group,
            stepType: stepType as EStepType,
            beforeStep: currentStep,
        })
        
        // Пересчитываем индексы для шагов ПОСЛЕ вставляемого, сохраняя UUID
        const recalculatedAfterInsertSteps = map(currentSteps.slice(insertPosition), (item, index) => {
            const updatedIndex = newStepIndex + index + 1
            
            const updatedId = getStepId({
                index: updatedIndex,
                group: item.step_group
            })
            
            return {
                ...item,
                localIndexStep: updatedIndex,
                localId: updatedId,
                part_num: updatedIndex + 1,
                part_all: newTotalSteps,
                // localUUID остается неизменным!
            }
        })
        
        /*
         * Собираем итоговый массив: шаги до вставки + новый шаг + пересчитанные шаги после
         * Пересчитываем part_num для ВСЕХ шагов, включая шаги до вставки
         */
        const updatedSteps = [
            ...currentSteps.slice(0, insertPosition).map((item, idx) => ({ 
                ...item, 
                part_num: idx + 1,
                part_all: newTotalSteps 
            })),
            newStep,
            ...recalculatedAfterInsertSteps
        ]

        const updatedRun = {
            ...currentRun,
            steps: updatedSteps
        } as IRunById

        // Автоматически добавляем новый шаг в редактирование (используем UUID)
        set({ currentRun: updatedRun })
        
        const editingSteps = get().editingSteps
        
        // Обновляем все существующие editingSteps с новыми данными из updatedSteps
        const updatedExistingEditingSteps = map(editingSteps, (editingStep) => {
            const updatedStepData = find(updatedSteps, (s) => s.localUUID === editingStep.id)

            if (updatedStepData) {
                // Обновляем только служебные поля, сохраняя отредактированные данные
                return {
                    ...editingStep,
                    step: {
                        ...editingStep.step,
                        part_num: updatedStepData.part_num,
                        part_all: updatedStepData.part_all,
                        localIndexStep: updatedStepData.localIndexStep,
                        localId: updatedStepData.localId
                    }
                }
            }

            return editingStep
        })
        
        const editingStep = { id: newStep.localUUID!, step: newStep }
        const updatedEditingSteps = [...updatedExistingEditingSteps, editingStep]

        set({ editingSteps: updatedEditingSteps })
    },
    removeStepFromRun: (stepUUID) => {
        const currentRun = get().currentRun
        const currentSteps = currentRun?.steps || []

        if (!size(currentSteps)) {
            return
        }

        // Находим индекс удаляемого шага по UUID
        const stepToRemoveIndex = currentSteps.findIndex((step) => step.localUUID === stepUUID)
        
        if (stepToRemoveIndex === -1) {
            return
        }

        const stepToRemove = currentSteps[stepToRemoveIndex]
        
        // Удаляем шаг только если он был создан локально
        if (!stepToRemove.isLocalCreated) {
            return
        }

        // Создаем новый массив шагов без удаляемого
        const stepsWithoutRemoved = currentSteps.filter((_, index) => index !== stepToRemoveIndex)
        const newTotalSteps = stepsWithoutRemoved.length

        // Пересчитываем индексы для всех шагов после удаленного
        const updatedSteps = map(stepsWithoutRemoved, (item, index) => {
            if (index < stepToRemoveIndex) {
                // Шаги до удаленного остаются без изменений
                return {
                    ...item,
                    part_all: newTotalSteps
                }
            }
            
            // Пересчитываем индексы для шагов после удаленного
            const newIndex = index
            const newStepId = getStepId({
                index: newIndex,
                group: item.step_group
            })
            
            return {
                ...item,
                localIndexStep: newIndex,
                localId: newStepId,
                part_num: newIndex + 1,
                part_all: newTotalSteps,
            }
        })

        const updatedRun = {
            ...currentRun,
            steps: updatedSteps
        } as IRunById

        set({ currentRun: updatedRun })
        
        const editingSteps = get().editingSteps
        
        // Удаляем шаг из editingSteps
        const editingStepsWithoutRemoved = reject(editingSteps, (step) => step.id === stepUUID)
        
        // Обновляем все оставшиеся editingSteps с новыми данными из updatedSteps
        const updatedEditingSteps = map(editingStepsWithoutRemoved, (editingStep) => {
            const updatedStepData = find(updatedSteps, (s) => s.localUUID === editingStep.id)

            if (updatedStepData) {
                // Обновляем только служебные поля, сохраняя отредактированные данные
                return {
                    ...editingStep,
                    step: {
                        ...editingStep.step,
                        part_num: updatedStepData.part_num,
                        part_all: updatedStepData.part_all,
                        localIndexStep: updatedStepData.localIndexStep,
                        localId: updatedStepData.localId
                    }
                }
            }

            return editingStep
        })
        
        set({ editingSteps: updatedEditingSteps })
    },
    setSelectedEditingStep: (step) => {
        set({ selectedEditingStep: step })
    },
    setGlobalLoader: (isGlobalLoader) => {
        set({ isGlobalLoader })
    },
    updateCurrentRun: (run) => {
        const currentRun = get().currentRun

        if (currentRun) {
            set({ currentRun: { ...currentRun, ...run } })
        }
    },
    setVariablesList: (variables) => {
        if (!variables) {
            set({ variablesList: {} })

            return
        }

        const prev = get().variablesList

        set({ variablesList: { ...prev, ...variables } })
    },
    setIsEdited: (isEdited) => {
        set({ isEdited })
    },
    setRefetchingState: (data) => {
        const refetchingState = {
            isRefetchingVideo: !isBoolean(data.video) ? get().isRefetchingVideo : data.video,
            isRefetchingSteps: !isBoolean(data.steps) ? get().isRefetchingVideo : data.steps
        }

        set({ ...refetchingState })
    },
    updateEditingStep: (stepUUID, step) => {
        const editingSteps = get().editingSteps

        if (!size(editingSteps)) {
            return
        }

        const updatedSteps = map(editingSteps, (item) => {
            if (stepUUID === item.id) {
                return {
                    id: stepUUID,
                    step: deepMerge(item.step, step)
                } as IEditingStep
            }

            return item
        })

        set({ editingSteps: updatedSteps })
    },
    setEditingStep: (editingStep) => {
        const prevData = get().editingSteps


        if (isArray(editingStep)) {
            if (size(editingStep) <= 0) {
                set({ editingSteps: [] })

                return
            }
            set({ editingSteps: [...prevData, ...editingStep] })

            return
        }

        if (editingStep) {
            prevData.push(editingStep)

            set({ editingSteps: prevData })
        }
    },
    removeEditingStep: (stepUUID) => {
        const prevData = get().editingSteps
        const updatedData = reject(prevData, (step) => step.id === stepUUID)

        set({ editingSteps: updatedData })
    },
    setIsLoading: (isLoading) => {
        set({ isLoading })
    },
    setError: (error) => {
        set({ error })
    },
    setInProgress: (inProgress) => {
        set({ inProgress })
    },
    setSelectedStep: (id, step, clicked = false) => {
        set({ selectedStep: { id, step, clicked } })
    },

    setOriginRun: (run) => {
        set({ originRun: run })
    },

    setCurrentRun: (run) => {
        if (run) {
            set({ currentRun: run, logs: run.steps })
        }
    },

    clearStore: () => {
        set({ ...initialState })
    }
})

const withDevtools = devtools(slice)
const store = create(withDevtools)

export const useRunningStore = createSelectors(store)

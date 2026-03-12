import { NEED_REFETCH_STATUSES, REFETCH_RUN_INTERVAL } from '@Common/consts/run.ts';
import { runsQueries } from '@Entities/runs/queries';
import { useRunningStore } from '@Pages/RunningCase/store';
import { prepareRunWithStepIds } from '@Pages/RunningCase/utils';
import { useQuery } from '@tanstack/react-query';
import includes from 'lodash/includes';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';


export const useRunningData = () => {
    const { runId } = useParams()
    const currentRun = useRunningStore((state) => state.currentRun)
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const selectedStep = useRunningStore((state) => state.selectedStep)
    const setSelectedEditingStep = useRunningStore((state) => state.setSelectedEditingStep)

    const needRefetchVideo = !currentRun?.video
    const needRefetchSteps = includes(NEED_REFETCH_STATUSES, currentRun?.status)

    const { data, isLoading, isError, error } = useQuery({
        ...runsQueries.runningCase(runId!!, {
            refetchInterval: () => {
                if (needRefetchSteps || needRefetchVideo) {
                    return REFETCH_RUN_INTERVAL
                }

                return undefined
            },
        }), retry: 2
    })
    const setRun = useRunningStore((state) => state.setCurrentRun)
    const setOriginRun = useRunningStore((state) => state.setOriginRun)
    const setError = useRunningStore((state) => state.setError)
    const setRefetchingState = useRunningStore((state) => state.setRefetchingState)
    const setLoading = useRunningStore((state) => state.setIsLoading)

    useEffect(() => {
        if (data) {
            // Получаем актуальное значение currentRun из стора, а не из замыкания
            const freshCurrentRun = useRunningStore.getState().currentRun
            const preparedRun = prepareRunWithStepIds(data, freshCurrentRun)

            if (preparedRun) {
                setRun(preparedRun)
            }

            setOriginRun(data)

            setRefetchingState({
                steps: needRefetchSteps,
                video: needRefetchVideo
            })
        }
    }, [data]);

    useEffect(() => {
        const step = editingSteps?.find((item) => item?.id === selectedStep?.id)

        if (step) {
            setSelectedEditingStep(step)
        }
    }, [editingSteps, selectedStep])

    useEffect(() => {
        setLoading(isLoading)

        setError(isError)
    }, [isLoading, isError]);

    return { data, isLoading, isError, error }
}

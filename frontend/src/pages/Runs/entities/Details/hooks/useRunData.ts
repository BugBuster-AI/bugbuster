import { PROGRESS_STATUSES } from '@Common/consts/run';
import { getErrorMessage } from '@Common/utils/getErrorMessage';
import { runsQueries } from '@Entities/runs/queries';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { useQuery } from '@tanstack/react-query';
import get from 'lodash/get';
import head from 'lodash/head';
import size from 'lodash/size';
import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';

export const useRunData = () => {
    const searchValue = useGroupedRunStore((state) => state.search)
    const setData = useGroupedRunStore((state) => state.setData)
    const setLoading = useGroupedRunStore((state) => state.setLoading)
    const setError = useGroupedRunStore((state) => state.setError)
    const filters = useGroupedRunStore((state) => state.filters)
    const pagination = useGroupedRunStore((state) => state.pagination)
    const setErrorMessage = useGroupedRunStore((state) => state.setErrorMessage)
    const isCaseFetching = useGroupedRunStore((state) => state.isCaseFetching)

    const fetchedTimes = useRef(0)

    const { id, runId } = useParams()

    const { data, isLoading, isError, error } = useQuery(runsQueries.groupedRunList({
        status: size(filters) > 0 ? filters : undefined,
        offset: pagination.pageSize * (pagination.page - 1),
        limit: pagination.pageSize,
        group_run_id: runId,
        project_id: id!,
        filter_cases: searchValue
    },
    !!id,
    {
        refetchInterval: (query) => {
            const items = get(query, 'state.data.items', null)
            const currentItem = head(items)

            if (!currentItem) {
                return 3000
            }

            /** TODO: убрать костыль, если пофиксится баг со status untested после запуска */
            if (!PROGRESS_STATUSES.includes(currentItem?.status) && fetchedTimes.current < 4) {
                fetchedTimes.current += 1

                return 3000
            }

            if (!currentItem || !PROGRESS_STATUSES.includes(currentItem.status) || isCaseFetching) {
                fetchedTimes.current = 0

                return undefined
            }

            return 3000
        }
    }))

    useEffect(() => {
        if (error) {
            const errorMessage = getErrorMessage({
                error,
                needConvertResponse: true
            })


            setErrorMessage(errorMessage)
        } else {
            setErrorMessage(undefined)
        }
    }, [error]);

    useEffect(() => {
        if (data) {
            setData(data)
        }
    }, [data, setData]);

    useEffect(() => {
        setError(isError)
        setLoading(isLoading)
    }, [isError, isLoading]);


    return { data, isLoading, isError }
}

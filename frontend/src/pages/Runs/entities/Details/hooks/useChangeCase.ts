import { URL_QUERY_KEYS } from '@Common/consts/searchParams.ts';
import { useTestCaseStore } from '@Entities/test-case';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { findCaseInGroupRun } from '@Pages/Runs/entities/Details/utils';
import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

export const useChangeCase = () => {
    const setOpenedCaseId = useGroupedRunStore((state) => state.setOpenedCaseId)
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)
    const setCurrentCaseSuite = useGroupedRunStore((state) => state.setCurrentCaseSuite)
    const run = useGroupedRunStore((state) => state.runItem)

    const [, updateSearchParams] = useSearchParams()

    return useCallback((id: string) => {
        const suites = run?.parallel

        const { case: currentCase, currentSuite } = findCaseInGroupRun(suites || [], id) || {}

        if (id && currentSuite) {
            setOpenedCaseId(id)
            setCurrentCase(currentCase)
            setCurrentCaseSuite(currentSuite)
            updateSearchParams((prev) => {
                prev.set(URL_QUERY_KEYS.CASE_ID, id)

                return prev
            })
        }
    }, [])
}

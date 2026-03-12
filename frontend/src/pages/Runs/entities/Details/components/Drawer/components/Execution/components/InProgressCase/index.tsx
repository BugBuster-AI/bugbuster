import { PROGRESS_STATUSES, REFETCH_RUN_INTERVAL } from '@Common/consts/run.ts';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { runsQueries } from '@Entities/runs/queries';
import { useTestCaseStore } from '@Entities/test-case';
import { RunStepsView } from '@Entities/test-case/components/StepsView/RunStepsView.tsx';
import { useLocalRunStepsData } from '@Entities/test-case/hooks/useLocalStepData.ts';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { useQuery } from '@tanstack/react-query';
import { Flex } from 'antd';
import get from 'lodash/get';
import includes from 'lodash/includes';
import { useEffect } from 'react';

export const InProgressCase = () => {
    const testCase = useTestCaseStore((state) => state.currentCase)
    const updateCurrentCase = useTestCaseStore((state) => state.updateCurrentCase)
    const setCaseFetching = useGroupedRunStore((state) => state.setCaseFetching)
    const { data, error } = useQuery(runsQueries.runningCase(testCase?.actual_run_id!, {
        refetchInterval: (query) => {
            const status = get(query, 'state.data.status', null)

            if (includes(PROGRESS_STATUSES, status)) {
                return REFETCH_RUN_INTERVAL
            } else if (!!status) {
                setCaseFetching(false)
            }

            return undefined
        },
    }))


    const errorMessage = getErrorMessage({
        error,
        needConvertResponse: true
    })

    useEffect(() => {
        if (data) {
            updateCurrentCase({
                actual_status: data.status,
            })
        }
    }, [data]);


    useEffect(() => {
        setCaseFetching(true)
    }, []);

    const { steps: localSteps } = useLocalRunStepsData({ run: data })

    return (
        <Flex>
            <RunStepsView
                attachments={ data?.attachments }
                errorMessage={ errorMessage }
                steps={ localSteps }
                grouping
            />
        </Flex>
    )
}

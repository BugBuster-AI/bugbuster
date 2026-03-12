import { needRefetchRun, REFETCH_RUN_INTERVAL } from '@Common/consts/run.ts';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { ResultCard } from '@Components/ResultCard';
import { VideoLoader } from '@Entities/runs/components/VideoLoader';
import { runsQueries } from '@Entities/runs/queries';
import { getRunInfo } from '@Entities/runs/utils/runInfo.ts';
import { useTestCaseStore } from '@Entities/test-case';
import { RunStepsView } from '@Entities/test-case/components/StepsView/RunStepsView.tsx';
import { useLocalRunStepsData } from '@Entities/test-case/hooks/useLocalStepData.ts';
import { useQuery } from '@tanstack/react-query';
import { Divider, Flex, Skeleton, Typography } from 'antd';
import get from 'lodash/get';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export const FinishedCase = () => {
    const testCase = useTestCaseStore((state) => state.currentCase)
    const { t } = useTranslation()
    const { data, isLoading, error } = useQuery(runsQueries.runningCase(testCase?.actual_run_id!!, {
        refetchInterval: (query) => {
            const data = get(query, 'state.data', null)

            const needRefetch = needRefetchRun(data)

            if (needRefetch) {
                return REFETCH_RUN_INTERVAL
            }

            return undefined
        }
    }))

    const errorMessage = getErrorMessage({
        error,
        needConvertResponse: true
    })


    const { isGeneratingVideo, hasVideo } = useMemo(() => getRunInfo(data), [data])

    const { steps: localSteps } = useLocalRunStepsData({ run: data })


    if (isLoading) return <Skeleton paragraph={ { width: '100%', rows: 3 } } title={ false }/>

    return (
        <Flex vertical>

            <Flex style={ { marginBottom: '12px' } } vertical>

                <Divider orientation="left" orientationMargin={ 0 } style={ { marginBottom: 4 } } plain>
                    <Typography.Title level={ 5 }>
                        {t('group_run.drawer.result')}
                    </Typography.Title>
                </Divider>
                {(data) &&
                    <ResultCard
                        result={ data?.run_summary || undefined }
                        status={ testCase?.actual_status! }
                        time={ data?.complete_time }
                    />}
            </Flex>

            <RunStepsView
                attachments={ data?.attachments }
                errorMessage={ errorMessage }
                steps={ localSteps }
                grouping
            />

            <Flex style={ { marginTop: 8 } }>
                {isGeneratingVideo && <VideoLoader/>}
                {hasVideo && (
                    <Typography.Link ellipsis={ true } href={ data?.video?.url } target="_blank">
                        {t('running_page.view_video')}
                    </Typography.Link>
                )}
            </Flex>
        </Flex>
    )
}

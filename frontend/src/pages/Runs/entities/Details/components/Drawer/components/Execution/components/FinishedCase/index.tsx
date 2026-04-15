import { needRefetchRun, REFETCH_RUN_INTERVAL } from '@Common/consts/run.ts';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { ResultCard } from '@Components/ResultCard';
import { VideoLoader } from '@Entities/runs/components/VideoLoader';
import { runsQueries } from '@Entities/runs/queries';
import { getRunInfo } from '@Entities/runs/utils/runInfo.ts';
import { useTestCaseStore } from '@Entities/test-case';
import { RunStepsView } from '@Entities/test-case/components/StepsView/RunStepsView.tsx';
import { useLocalRunStepsData } from '@Entities/test-case/hooks/useLocalStepData.ts';
import { ETestCaseType } from '@Entities/test-case/models';
import { ErrorBoundary } from '@Common/components/ErrorBoundary';
import { CodegenExecutionViewSwitch, TCodegenExecutionView } from '@Features/test-case/playwright-codegen/CodegenExecutionViewSwitch.tsx';
import { PlaywrightCodegenPanel } from '@Features/test-case/playwright-codegen/PlaywrightCodegenPanel.tsx';
import { useQuery } from '@tanstack/react-query';
import { Divider, Flex, Skeleton, Typography } from 'antd';
import get from 'lodash/get';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const FinishedCase = () => {
    const testCase = useTestCaseStore((state) => state.currentCase)
    const { t } = useTranslation()
    const [executionView, setExecutionView] = useState<TCodegenExecutionView>('run')
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

    const { steps: localStepsGrouped } = useLocalRunStepsData({ run: data })

    const showCodegen = testCase?.type === ETestCaseType.automated
        && Boolean(data?.run_id) && Boolean(testCase?.case_id)

    if (isLoading) return <Skeleton paragraph={ { width: '100%', rows: 3 } } title={ false }/>

    return (
        <Flex
            style={ {
                flex: 1,
                height: '100%',
                minHeight: 0,
            } }
            vertical
        >

            <Flex style={ { marginBottom: '12px' } } vertical>

                <Divider orientation="left" orientationMargin={ 0 } style={ { marginBottom: 4 } } plain>
                    <Typography.Title level={ 5 }>
                        {t('group_run.drawer.result')}
                    </Typography.Title>
                </Divider>
                {(data) &&
                    <ResultCard
                        result={ data?.run_summary || undefined }
                        resultFormat="ansi"
                        status={ testCase?.actual_status! }
                        time={ data?.complete_time }
                    />}
            </Flex>

            {showCodegen && testCase?.case_id && data?.run_id && (
                <CodegenExecutionViewSwitch
                    onChange={ setExecutionView }
                    value={ executionView }
                />
            )}

            {showCodegen && executionView === 'codegen' && testCase?.case_id && data?.run_id
                ? (
                    <div
                        style={ {
                            display: 'flex',
                            flex: 1,
                            flexDirection: 'column',
                            minHeight: 0,
                            overflow: 'auto',
                        } }
                    >
                        <ErrorBoundary>
                            <PlaywrightCodegenPanel
                                caseId={ String(testCase.case_id) }
                                runId={ data.run_id }
                                testCase={ testCase }
                                embedded
                            />
                        </ErrorBoundary>
                    </div>
                )
                : (
                    <RunStepsView
                        attachments={ data?.attachments }
                        errorMessage={ errorMessage }
                        steps={ localStepsGrouped }
                        grouping
                    />
                )}

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

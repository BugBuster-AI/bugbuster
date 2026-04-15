import { ErrorBoundary } from '@Common/components/ErrorBoundary';
import { ResultCard } from '@Common/components/ResultCard';
import { useThemeToken } from '@Common/hooks';
import { ERunStatus } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ETestCaseType } from '@Entities/test-case/models';
import { CodegenExecutionViewSwitch } from '@Features/test-case/playwright-codegen/CodegenExecutionViewSwitch.tsx';
import { codegenHighlightUidFromRunStep } from '@Features/test-case/playwright-codegen/codegenHighlightUid.ts';
import { PlaywrightCodegenPanel } from '@Features/test-case/playwright-codegen/PlaywrightCodegenPanel.tsx';
import { ApiDetails } from '@Pages/RunningCase/components/Content/components/ApiDetails';
import { DefaultDetails } from '@Pages/RunningCase/components/Content/components/DefaultDetails';
import { Stepper } from '@Pages/RunningCase/components/Stepper';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Empty, Flex, Image, Spin } from 'antd';
import find from 'lodash/find';
import get from 'lodash/get';
import map from 'lodash/map';
import size from 'lodash/size';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export const RunningContent = () => {
    const token = useThemeToken()
    const { t } = useTranslation()
    const selectedStep = useRunningStore((state) => state.selectedStep)
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const run = useRunningStore((state) => state.currentRun)
    const originRun = useRunningStore((state) => state.originRun)
    const executionPanelView = useRunningStore((state) => state.executionPanelView)
    const setExecutionPanelView = useRunningStore((state) => state.setExecutionPanelView)

    const showCodegen =
        originRun?.case?.type === ETestCaseType.automated &&
        Boolean(originRun?.run_id) &&
        Boolean(originRun?.case?.case_id)

    const currentEditingStep = find(editingSteps, (item) => item.id === selectedStep?.id)
    const isEditing = !!currentEditingStep


    const getStep = () => {
        if (isEditing) {
            return get(currentEditingStep, 'step', null)
        }
        if (selectedStep?.step?.checkResults) {
            return get(selectedStep, 'step', null)
        }

        return get(selectedStep, 'step', null)
    }
    // checkResults - появляется после сохранения кейса
    const step = getStep()
    const codegenHighlightUid = useMemo(
        () => codegenHighlightUidFromRunStep(step ?? undefined, originRun?.case),
        [step, originRun?.case],
    )
    const isChecked = step?.checkResults
    const isExpectedResult = step?.step_type === EStepType.RESULT && step?.validation_result

    let Details

    switch (step?.step_type) {
        case EStepType.API:
            Details = ApiDetails
            break
        default:
            Details = DefaultDetails
            break
    }

    if (showCodegen && executionPanelView === 'codegen' && originRun?.case?.case_id && originRun.run_id) {
        return (
            <Flex
                style={ {
                    width: '100%',
                    height: '100%',
                    overflow: 'hidden',
                    position: 'relative',
                    flexDirection: 'column',
                } }
                vertical
            >
                <div
                    style={ {
                        background: token.colorBgContainer,
                        borderBottom: `1px solid ${token.colorBorder}`,
                        flexShrink: 0,
                        padding: '12px 24px 0',
                        position: 'sticky',
                        top: 0,
                        zIndex: 2,
                    } }
                >
                    <CodegenExecutionViewSwitch
                        onChange={ setExecutionPanelView }
                        value={ executionPanelView }
                    />
                </div>
                <div
                    style={ {
                        display: 'flex',
                        flex: 1,
                        flexDirection: 'column',
                        minHeight: 0,
                        overflow: 'auto',
                        padding: '8px 24px 48px',
                    } }
                >
                    <ErrorBoundary>
                        <PlaywrightCodegenPanel
                            caseId={ String(originRun.case.case_id) }
                            highlightStepUid={ codegenHighlightUid }
                            runId={ originRun.run_id }
                            testCase={ originRun.case }
                            embedded
                        />
                    </ErrorBoundary>
                </div>
            </Flex>
        )
    }

    if (step?.isLoading) {
        return (
            <div style={ { padding: 20, height: '100%', width: '100%' } }>
                <Spin style={ { left: '50%', top: '50%' } }/>
            </div>
        )
    }

    return (
        <Flex
            style={ {
                width: '100%',
                position: 'relative',
                overflow: 'auto',
                flexDirection: 'column',
                height: '100%',
            } }
        >

            {showCodegen && (
                <div
                    style={ {
                        background: token.colorBgContainer,
                        borderBottom: `1px solid ${token.colorBorder}`,
                        flexShrink: 0,
                        padding: '12px 24px 0',
                    } }
                >
                    <CodegenExecutionViewSwitch
                        onChange={ setExecutionPanelView }
                        value={ executionPanelView }
                    />
                </div>
            )}

            <Flex style={ { flex: 1, minHeight: 0, overflow: 'auto', width: '100%' } }>

                <Stepper/>

                <Flex
                    style={ {
                        overflow: 'auto',
                        backgroundColor: token.colorFillTertiary,
                        padding: '16px 24px 48px',
                        flex: 1,
                        alignItems: 'flex-start',
                        flexDirection: 'column',
                        position: 'relative',
                        width: '100%',
                        justifyContent: !step ? 'center' : 'initial'
                    } }>

                    {step ? <>
                        {step?.checkResults && (
                            <ResultCard
                                result={ step?.checkResults?.description }
                                size="medium"
                                status={  step?.checkResults?.status }
                                time={ step?.checkResults?.time }
                                title={ step?.checkResults?.title }
                                needIcon
                            />
                        )
                        }
                        {isExpectedResult &&  (
                            <ResultCard
                                result={ step?.validation_result?.reflection_description }
                                size="medium"
                                status={  step?.validation_result?.reflection_result! }
                                time={ step?.validation_result?.reflection_time }
                                title={ step?.validation_result?.reflection_title }
                                needIcon
                            />
                        ) }
                        {(!isExpectedResult && step.status_step === ERunStatus.FAILED && !isChecked) &&
                        <ResultCard
                            result={ run?.run_summary  }
                            resultFormat="ansi"
                            size="medium"
                            status={  false }
                            time={ step?.validation_result?.reflection_time }
                            title={  t('statuses.failed') }
                            needIcon
                        />
                        }
                        {size(step.attachments) > 0 && (
                            <Flex vertical>
                                {map(step.attachments, (item) => <Image key={ item.url } src={ item.url }/>)}
                            </Flex>
                        )}
                        <Details/>
                    </> : (

                        <Flex style={ { alignSelf: 'center', height: 'fit-content' } }>
                            <Empty/>
                        </Flex>
                    )
                    }
                </Flex>
            </Flex>
        </Flex>
    )
}

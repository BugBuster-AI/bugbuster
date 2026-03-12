import { LoadingOutlined } from '@ant-design/icons';
import { EStatusIndicator } from '@Common/components';
import { ResultCard } from '@Common/components/ResultCard';
import { StepAccordion } from '@Common/components/StepAccordion';
import { NEED_REFETCH_STATUSES } from '@Common/consts/run.ts';
import { useThemeToken } from '@Common/hooks';
import { getRunStatusToIndicator } from '@Common/utils/common';
import { VideoLoader } from '@Entities/runs/components/VideoLoader';
import { ERunStatus, IRunStep, TStepGroup } from '@Entities/runs/models';
import { getFormattedStepInfo } from '@Entities/runs/utils/getFormattedStepInfo.tsx';
import { getRunInfo } from '@Entities/runs/utils/runInfo.ts';
import { convertStepType } from '@Entities/runs/utils/stepType.ts';
import { SingleRunStepCard } from '@Pages/RunningCase/components';
import { SharedStepGroup } from '@Pages/RunningCase/components/LogsList/components';
import { groupSharedSteps, IGroupedStep } from '@Pages/RunningCase/components/LogsList/utils';
import { useRunningStore } from '@Pages/RunningCase/store';
import { isNotUntestedStep } from '@Pages/RunningCase/utils/isNotUntestedStep.ts';
import { Divider, Flex, Spin, Typography } from 'antd';
import find from 'lodash/find';
import findLastIndex from 'lodash/findLastIndex';
import groupBy from 'lodash/groupBy';
import includes from 'lodash/includes';
import map from 'lodash/map';
import size from 'lodash/size';
import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useShallow } from 'zustand/react/shallow';


const LogsGroup =
    ({ logs, loadingStep }: { logs: IRunStep[], loadingStep?: IRunStep, groupName: string }) => {
        const selectedStep = useRunningStore(useShallow((state) => state.selectedStep))
        const setSelectedStep = useRunningStore(useShallow((state) => state.setSelectedStep))
        const run = useRunningStore((state) => state.currentRun)
        const token = useThemeToken()
        const editingSteps = useRunningStore((state) => state.editingSteps)

        const selectedExtra = selectedStep?.step?.extra
        const isStepsEditable = !includes(NEED_REFETCH_STATUSES, run?.status)

        const handleCardClick =
            (stepId: string, step: Partial<IRunStep>, clicked: boolean, clickable: boolean) => {
                if (!clickable) return

                setSelectedStep(stepId, step, clicked)
            }

        // Группируем степы по shared_step_id и shared_step_index
        const groupedSteps = useMemo(() => groupSharedSteps(logs), [logs])

        if (!size(logs)) return null

        const renderStep = (initialStep: IRunStep, index: number, sharedStep?: {index: number, size: number}) => {
            const editingStep = find(editingSteps, ['id', initialStep.localUUID || ''])
            const isEditing = !!editingStep

            const step = !!editingStep ? editingStep.step : initialStep
            
            const stepId = step.localUUID || ''
            const { actionName, titleComponent } = getFormattedStepInfo(step, {
                needMethodInApi: false
            })

            const stepInfo = `${step.part_num} / ${step.part_all}`

            const status = getRunStatusToIndicator(step.status_step)

            // Вставленные шаги всегда кликабельны
            const isClickable = step.isLocalCreated || status !== EStatusIndicator.IDLE
            const cursor = isClickable ? 'pointer' : 'default'

            const isActive = selectedStep?.id === step.localUUID

            const handleClickStep = () => {
                handleCardClick(stepId, step, true, isClickable)
            }

            // если проставлен флаг context_screenshot_used, либо локально включен isEnabled и есть скриншот
            const needContextIcon = step 
                && (step.extra?.context_screenshot_used) || 
                (step?.extra?.context_screenshot_path && step?.contextScreenshotMode?.isEnabled)

            const isDisabled = status === EStatusIndicator.IDLE && !initialStep?.isLocalCreated
            let canInsertStepAfter = false

            if (!sharedStep || sharedStep.index === sharedStep.size - 1) {
                canInsertStepAfter = ((step.step_group !== 'before_browser' && isActive) || isEditing)
            }

            return (
                <SingleRunStepCard
                    key={ step.localUUID || `running-log-${index}` }
                    actionName={ actionName }
                    canInsertStepAfter={ canInsertStepAfter }
                    contextIcon={ !!needContextIcon }
                    disabled={ isDisabled }
                    editable={ isStepsEditable }
                    extra={ initialStep?.extra ?? undefined }
                    isEditing={ isEditing }
                    isLoading={
                        loadingStep?.localUUID === step?.localUUID &&
                        run?.status === ERunStatus.IN_PROGRESS
                    }
                    isSelected={ isActive }
                    onClick={ handleClickStep }
                    originalTitle={ step?.raw_step_description || step?.original_step_description }
                    status={ status }
                    statusProps={ {
                        type: convertStepType(step.step_type, true)
                    } }
                    stepId={ stepId }
                    stepIndex={ step?.part_num }
                    stepInfo={ stepInfo }
                    stepItem={ step }
                    stepType={ step.step_type }
                    style={ {
                        border: isActive ? `1px solid ${token.colorText}` : '1px solid transparent', cursor
                    } }
                    time={ step?.step_time || false }
                    title={ titleComponent || '' }
                />
            )
        }

        return (
            <Flex gap={ 8 } vertical>
                {map(groupedSteps, (groupedItem: IGroupedStep, groupIndex) => {
                    if (groupedItem.type === 'single' && groupedItem.step) {
                        return renderStep(groupedItem.step, groupIndex)
                    }

                    if (groupedItem.type === 'shared_group' && groupedItem.steps) {
                        const groupKey = [groupedItem.sharedStepId, groupedItem.sharedStepIndex].join('-')
                        const extraData = selectedExtra 
                            ? [selectedExtra?.shared_step_id, selectedExtra?.shared_step_group_index].join('-') : null
                        const isSelected = extraData === groupKey

                        return (
                            <SharedStepGroup
                                key={ `shared-group-${groupKey}` }
                                groupName={ groupedItem.sharedStepId }
                                isSelected={ isSelected }
                                stepCount={ groupedItem.steps.length }
                            >
                                <Flex gap={ 8 } vertical>
                                    {map(groupedItem.steps, (step, stepIndex) => renderStep(step, stepIndex, {
                                        index: stepIndex,
                                        size: groupedItem.steps!.length
                                    }))}
                                </Flex>
                            </SharedStepGroup>
                        )
                    }

                    return null
                })}
            </Flex>
        )
    }

export const LogsList = () => {
    const run = useRunningStore((state) => state.currentRun)
    const editingsSteps = useRunningStore((state) => state.editingSteps)
    const editingStepsSize = size(editingsSteps)
    const runSteps = run?.steps || []
    const { t } = useTranslation()
    const selectedStep = useRunningStore((state) => state.selectedStep)
    const setSelectedStep = useRunningStore((state) => state.setSelectedStep)
    const setEditingSteps = useRunningStore((state) => state.setEditingStep)
    const isFinishRun = !includes(NEED_REFETCH_STATUSES, run?.status)

    useEffect(() => {
        setEditingSteps([])
    }, []);

    const stepGroups = useMemo(
        () => groupBy(runSteps, 'step_group') as Record<TStepGroup, IRunStep[]>,
        [runSteps]
    )

    /** REFACTORED: новый формат */
    const stepLoading = useMemo(() => find(runSteps, (step: IRunStep, index) => {
        if (isNotUntestedStep(step)) return false
        const prevStep = runSteps[index - 1]

        return !prevStep ||
            (prevStep && prevStep.status_step !== ERunStatus.FAILED);

    }), [runSteps])

    useEffect(() => {
        // обновляем выбранный степ при изменении рана
        if (!selectedStep || !isFinishRun && !runSteps) return

        const findSelectedStep = find(runSteps, (item) => item.localUUID === selectedStep.id)

        if (findSelectedStep) {
            setSelectedStep(selectedStep.id, findSelectedStep, selectedStep.clicked)
        }
    }, [runSteps, isFinishRun, editingStepsSize]);

    // Установка последнего степа - выбранным при загрузке рана
    useEffect(() => {
        if ((!selectedStep || !selectedStep?.clicked) && size(runSteps)) {
            const lastIndex = findLastIndex(runSteps, isNotUntestedStep);

            const stepItem = runSteps?.[lastIndex]

            if (lastIndex !== -1) setSelectedStep(stepItem.localUUID!, stepItem, false)
        }
    }, [runSteps, setSelectedStep])

    const { isGeneratingVideo, isInProgress, isInFinish } = useMemo(() => getRunInfo(run), [run])

    return (
        <Flex gap={ 8 } vertical>

            {(stepGroups?.before_browser && size(stepGroups?.before_browser)) &&
                <StepAccordion label={ t(`stepGroups.before_browser_start`) }>
                    <LogsGroup
                        groupName={ 'before_browser_start' }
                        loadingStep={ stepLoading }
                        logs={ stepGroups?.before_browser }
                    />
                </StepAccordion>
            }

            {(stepGroups?.before && size(stepGroups?.before)) &&
                <StepAccordion label={ t(`steps.before_steps`) }>
                    <LogsGroup
                        groupName={ 'before_steps' }
                        loadingStep={ stepLoading }
                        logs={ stepGroups?.before }
                    />
                </StepAccordion>
            }

            {(stepGroups?.step && size(stepGroups?.step)) &&
                <StepAccordion label={ t(`steps.steps`) }>
                    <LogsGroup
                        groupName={ 'steps' }
                        loadingStep={ stepLoading }
                        logs={ stepGroups?.step }
                    />
                </StepAccordion>
            }

            {(stepGroups?.after && size(stepGroups?.after)) &&
                <StepAccordion label={ t(`steps.after_steps`) }>
                    <LogsGroup
                        groupName={ 'after_steps' }
                        loadingStep={ stepLoading }
                        logs={ stepGroups?.after }
                    />
                </StepAccordion>
            }

            {/* Result */}
            {run && (isInProgress ?
                <Spin indicator={ <LoadingOutlined spin/> } style={ { marginTop: '20px' } }/>
                :

                (
                    <Flex style={ { marginBottom: '8px' } } vertical>
                        <Divider orientation="left" orientationMargin={ 0 } style={ { marginBottom: 4 } } plain>
                            <Typography.Title level={ 5 }>
                                {t('steps.result')}
                            </Typography.Title>
                        </Divider>

                        <ResultCard
                            result={ run?.run_summary }
                            status={ run.status }
                            time={ run?.complete_time }
                        />
                    </Flex>
                )
            )}

            {isGeneratingVideo && <VideoLoader/>}
            {isInFinish && <Typography.Link ellipsis={ true } href={ run?.video?.url } target="_blank">
                {t('running_page.view_video')}
            </Typography.Link>}

        </Flex>
    )
}

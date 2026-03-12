import { ClockCircleOutlined, LinkOutlined } from '@ant-design/icons';
import SquareIcon from '@Assets/icons/square.svg?react'
import { StatusBadge } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ERunStatus, IRunById } from '@Entities/runs/models';
import { TestTypeIcon } from '@Entities/test-case/components/Icons';
import { useStopCaseRunning, useUpdateTestCase } from '@Entities/test-case/queries';
import { serverErrorHandler } from '@Entities/test-case/utils/serverErrorHandler.ts';
import { RunButton as RunCaseButton } from '@Features/test-case/buttons';
import { IRunButtonRef } from '@Features/test-case/buttons/run-button.tsx';
import { createNewContextScreenshots, findStepsByError, mergeSteps } 
    from '@Pages/RunningCase/components/Header/components/ControlPanel/helper.ts';
import { useRunningStore } from '@Pages/RunningCase/store';
import { IEditingStep } from '@Pages/RunningCase/store/models.ts';
import { isNotUntestedStep } from '@Pages/RunningCase/utils/isNotUntestedStep.ts';
import { runToCase } from '@Pages/RunningCase/utils/runToCase.ts';
import { Button, Flex, message, Progress, Typography } from 'antd';
import dayjs from 'dayjs'
import get from 'lodash/get';
import isArray from 'lodash/isArray';
import map from 'lodash/map';
import omit from 'lodash/omit';
import reduce from 'lodash/reduce';
import size from 'lodash/size';
import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const ControlPanel = () => {
    const { t } = useTranslation()
    const currentRun = useRunningStore((state) => state.currentRun)
    const setCurrentRun = useRunningStore((state) => state.setCurrentRun)
    const originRun = useRunningStore((state) => state.originRun)
    const clearStore = useRunningStore((state) => state.clearStore)
    const setEditingSteps = useRunningStore((state) => state.setEditingStep)
    const setGlobalLoader = useRunningStore((state) => state.setGlobalLoader)
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const variablesList = useRunningStore((state) => state.variablesList)
    const isEditingCase = size(editingSteps) > 0

    const caseId = get(currentRun, 'case.case_id', null)
    const { mutateAsync } = useStopCaseRunning()
    const endDate = currentRun?.end_dt;
    const [stopLoading, setStopLoading] = useState(false)
    const formattedEndDate = endDate ? dayjs(endDate).format('DD.MM.YYYY HH:mm:ss') : null;
    const { mutateAsync: updateTestCase, isPending: updatingCase } = useUpdateTestCase(true)
    const runCaseRef = useRef<IRunButtonRef | null>(null)
    const totalSteps = size(get(originRun, 'steps', []))
    const readySteps = size(get(originRun, 'steps', []).filter(isNotUntestedStep))

    const progress = readySteps / totalSteps * 100

    const editingState = useMemo(() => reduce(editingSteps, (acc, item) => {
        const error = item?.step?.error
        const loading = item?.step?.isLoading

        const initialLoading = acc?.isLoading
        const initialError = acc?.isError

        acc.isLoading = !initialLoading ? !!loading : initialLoading
        acc.isError = !initialError ? !!error : initialError

        return acc
    }, { isLoading: false, isError: false }), [editingSteps])

    const handleStop = async () => {
        if (!currentRun) return

        setStopLoading(true)
        await asyncHandler(mutateAsync.bind(null, currentRun.run_id), {
            successMessage: t('test_case_run.stopped')
        })

        setStopLoading(false)
    }

    const handleTrace = () => {
        const trace = currentRun?.show_trace

        if (!trace) return

        window.open(trace, '_blank')
    }

    const handleCopy = async () => {
        await navigator.clipboard.writeText(window.location.href)

        await message.success(t('common.copied'))
    }

    const isProgress = currentRun?.status === ERunStatus.IN_QUEUE || currentRun?.status === ERunStatus.IN_PROGRESS

    const stopInProgress = currentRun?.status === ERunStatus.STOP_IN_PROGRESS

    const runAndSave = async () => {
        if (!currentRun) return
        try {
            setGlobalLoader(true)
            // генерируем контекстные скриншоты под новые степы
            const stepsWithContextScreenshots = await createNewContextScreenshots(editingSteps)

            if (stepsWithContextScreenshots.status === 0) {
                message.error(t('running_page.errors.saving.context_screenshots'))
                setGlobalLoader(false)

                return
            }

            const currentEditedSteps = stepsWithContextScreenshots.steps
            // сначала передаем все отредактированные степы в нормальные степы рана
            const mergedRunSteps = mergeSteps(currentRun.steps, currentEditedSteps, variablesList)

            // обновляем ран с новыми степами
            const updatedRun = {
                ...currentRun,
                steps: mergedRunSteps,
            } as IRunById

            // формируем обновленный кейс из рана
            const updatedCase = omit(runToCase(updatedRun),
                ['action_plan', 'attachments', 'original_case'])

            //@ts-ignore
            updatedRun.case = updatedCase

            setCurrentRun(updatedRun)
            setEditingSteps([])

            //@ts-ignore
            await asyncHandler(() => updateTestCase(updatedCase), {
                errorMessage: null,
                onSuccess: () => {
                    runCaseRef?.current?.handleClick()
                },
                onError: (e) => {
                    const objError = serverErrorHandler({ error: e })


                    if (isArray(objError)) {
                        message.error(`Error when saving case: ${JSON.stringify(objError)}`)
                        /*
                         * setCurrentRun(prevRun)
                         * setEditingSteps([])
                         */

                        return
                    }

                    if (typeof objError === 'string') {
                        message.error(objError)
                        
                        console.error('error === string')
                        setEditingSteps(stepsWithContextScreenshots?.steps)

                        return
                    }

                    if (objError) {
                        if (objError?.message) {
                            message.error(objError.message)
                        } else {
                            const erroredSteps = findStepsByError(updatedRun.steps, objError as any)

                            console.error('error === object')
                            const editingSteps = map(erroredSteps, (step) => ({
                                id: step.localUUID,
                                step
                            })) as IEditingStep[]
                            
                            setEditingSteps(editingSteps)
                        }
                    }
                }
            })
            setGlobalLoader(false)

        } catch (e) {
            console.error(e)
        } finally {
            setGlobalLoader(false)
        }

    }

    if (!currentRun) return null

    return (
        <Flex align={ 'center' } gap={ 24 }>
            <Flex align={ 'center' } gap={ 16 }>
                <div style={ { display: 'flex' } }>
                    <TestTypeIcon style={ { marginRight: '8px' } } type={ currentRun?.case?.case_type_in_run }/>
                    {formattedEndDate || (
                        <Progress
                            percent={ progress - 5 }
                            showInfo={ false }
                            style={ { width: '140px' } }
                        />
                    )
                    }
                </div>

                <StatusBadge status={ currentRun.status }/>

                <Typography.Text>
                    <ClockCircleOutlined style={ { marginRight: '8px' } }/>
                    {formatSeconds(Number(currentRun.complete_time || 0), t)}
                </Typography.Text>

            </Flex>

            <Flex align={ 'center' } gap={ 16 }>
                <Flex align={ 'center' } gap={ 8 }>

                    <Button
                        disabled={ !currentRun.show_trace }
                        onClick={ handleTrace }
                    >
                        {t('running_page.buttons.trace')}
                    </Button>

                    <Button icon={ <LinkOutlined/> } onClick={ handleCopy }/>
                </Flex>

                {(isEditingCase || updatingCase) && (
                    <Button
                        disabled={ editingState.isError || editingState.isLoading }
                        htmlType={ 'button' }
                        loading={ updatingCase || editingState.isLoading }
                        onClick={ runAndSave }
                        type={ 'primary' }
                        variant={ 'solid' }
                    >
                        {t('common.save_run')}
                    </Button>
                )}
                {(!isProgress && !stopInProgress) && (
                    <div style={ { display: (isEditingCase || updatingCase) ? 'none' : 'initial' } }>

                        <RunCaseButton
                            ref={ runCaseRef }
                            case_id={ caseId!! }
                            disabled={ isEditingCase }
                            isTargetBlank={ false }
                            onClick={ clearStore }
                            props={ {
                                type: 'primary',
                            } }
                        />
                    </div>
                )}
                {(isProgress || stopInProgress) && (
                    <Button 
                        icon={ <SquareIcon style={ { strokeWidth: 2, width: 16, height: 16 } }/> } 
                        loading={ stopInProgress || stopLoading }
                        onClick={ handleStop }
                    >
                        {t('running_page.buttons.stop')}
                    </Button>
                )}
            </Flex>
        </Flex>
    )
}

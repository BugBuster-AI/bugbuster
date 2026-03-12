import { StatusIndicator } from '@Common/components';
import { IEditCardInfo, ManualEditCard } from '@Common/components/ManualEditCard';
import { IError } from '@Common/types';
import { asyncHandler } from '@Common/utils';
import { getRunStatusToIndicator } from '@Common/utils/common.ts';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { getMedias } from '@Common/utils/getMedias.ts';
import { isSharedStep } from '@Common/utils/test-case/consts.ts';
import { StepsDataView } from '@Components/StepsDataView';
import { ERunStatus, IMedia } from '@Entities/runs/models';
import { runsQueries } from '@Entities/runs/queries';
import { usePassTestStep } from '@Entities/runs/queries/mutations.ts';
import { getFormattedStepInfo } from '@Entities/runs/utils/getFormattedStepInfo.tsx';
import { getReflectionRunStatus } from '@Entities/runs/utils/getReflectionStatus.ts';
import { convertStepType } from '@Entities/runs/utils/stepType.ts';
import { useTestCaseStore } from '@Entities/test-case';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { AddRunResult } from '@Pages/Runs/entities/Details/components/Drawer/components/Execution/components/AddResult';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { useQuery } from '@tanstack/react-query';
import { Flex, message, Spin, Steps } from 'antd';
import { AxiosError } from 'axios';
import entries from 'lodash/entries';
import find from 'lodash/find';
import get from 'lodash/get';
import isEmpty from 'lodash/isEmpty';
import nth from 'lodash/nth';
import reduce from 'lodash/reduce';
import { useEffect, useMemo, useState } from 'react';

export interface IManualStepValue {
    comment?: string;
    status: ERunStatus;
    files?: File[]
    attachments?: IMedia[]
    label?: string
    formKey?: string

}

const getItemFormKey = (index: number, resultIndex: number) => `${index}-${resultIndex}`

export const ManualEdit = () => {
    const [formValue, setFormValue] = useState<Record<string | number, IManualStepValue>>({})
    const testCase = useTestCaseStore((state) => state.currentCase)
    const [tempFailedData, setTempFailedData] = useState<IManualStepValue | undefined>(undefined)
    const runItem = useGroupedRunStore((state) => state.runItem)
    const [initialLoaded, setInitialLoaded] = useState(false)
    const [loading, setLoading] = useState(false)
    const [resultOpen, setResultOpen] = useState<undefined | {
        index: number,
        open: boolean,
        reflectionIndex?: number
    }>(undefined)

    const { mutateAsync, isPending } = usePassTestStep(runItem?.group_run_id!)
    const {
        data,
        isLoading,
        isRefetching,
        error
    } = useQuery(runsQueries.runningCase(testCase?.actual_run_id!, { refetch: false, gcTime: 0 }))

    const handleDeleteFormValue = (index: string) => {
        setFormValue((prev) => {
            const newValue = { ...prev }

            if (index) {
                delete newValue[index]
            }

            return newValue
        })

    }

    const handleCloseResultWindow = () => {
        setResultOpen(undefined)
    }

    const handleFailed = ({ index, info, reflectionIndex }: {
        index: number,
        info?: IEditCardInfo,
        reflectionIndex?: number
    }) => {
        const { files, comment } = info || {}

        setTempFailedData({
            status: ERunStatus.FAILED,
            files,
            comment
        })
        setResultOpen({ index, open: true, reflectionIndex })
    }

    const errorMessage = getErrorMessage({
        error,
        needConvertResponse: true
    })

    const handleClick = async (
        {
            index,
            status,
            info,
            reflectionIndex,
            formKey
        }: {
            index: number,
            status?: ERunStatus,
            info?: { comment?: string, files?: File[], prevStatus?: ERunStatus },
            reflectionIndex?: number
            formKey?: string
        }
    ) => {

        if (status === ERunStatus.PASSED) {
            try {
                const medias = await getMedias(info?.files)

                await asyncHandler(mutateAsync.bind(null, {
                    run_id: testCase?.actual_run_id!,
                    comment: info?.comment || undefined,
                    passed_step_index: Number(index),
                    attachments: medias || undefined,
                    reflection_step_index: reflectionIndex
                }), {
                    onError: () => {
                        if (formKey) {
                            handleDeleteFormValue(formKey)
                        }
                    }
                })
            } catch (e) {
                const axiosError = e as AxiosError<IError>
                const error = axiosError?.response?.data?.detail || 'Something went wrong...'

                message.error(error)

                if (formKey) {
                    handleDeleteFormValue(formKey)
                }

                return
            }
        }
        if (!status) {
            setFormValue((prev) => {
                const newState = { ...prev }

                delete newState[index]

                return newState
            })

            return
        }

        if (status) {
            if (formKey) {

                setFormValue((prev) => ({
                    ...prev,
                    [formKey]: { status, comment: info?.comment }
                }))
            }
        }
    }

    useEffect(() => {
        if (isEmpty(formValue) && data?.steps && !initialLoaded) {
            const loadDefaultValues = () => {
                const defaultValues = reduce(data?.steps, (acc, item) => {
                    const formKey = getItemFormKey(item.index_step, 0)

                    if (item.step_type === EStepType.RESULT) {
                        acc[formKey] = {
                            status: getReflectionRunStatus(item?.validation_result?.reflection_result),
                            comment: item?.validation_result?.reflection_description,
                            attachments: item?.validation_result?.attachments,
                            label: item?.validation_result?.reflection_step,
                        }
                    } else {
                        acc[formKey] = {
                            status: item.status_step,
                            comment: item.comment,
                            attachments: item?.attachments,
                            label: item?.original_step_description,
                        }
                    }

                    return acc
                }, {} as Record<number | string, IManualStepValue>)

                // Обновляем состояние
                setFormValue((prev) => ({
                    ...defaultValues,
                    ...prev
                }));
                setInitialLoaded(true)
                setLoading(false)
            };

            loadDefaultValues();

        }


    }, [runItem, data, initialLoaded]);

    const activeStep = useMemo(() => {
        const foundStep = find(entries(formValue), ([, value]) => value.status === ERunStatus.UNTESTED)

        return nth(foundStep, 0)
    }, [formValue])

    return (
        <Spin spinning={ isRefetching || isLoading || loading }>
            <Flex vertical>
                {resultOpen?.open &&
                    <AddRunResult
                        defaultStatus={ ERunStatus.FAILED }
                        defaultValues={ {
                            comment: tempFailedData?.comment,
                            attachments: tempFailedData?.files,
                            status: tempFailedData?.status || ERunStatus.FAILED
                        } }
                        isStatusChangeable={ false }
                        onClose={ handleCloseResultWindow }
                        open={ resultOpen?.open }
                        reflectionIndex={ resultOpen?.reflectionIndex }
                        stepIndex={ resultOpen?.index }
                    />}
                <StepsDataView
                    error={ errorMessage }
                    renderLog={ ({ step: item }) => {
                        const itemIndex = item.index_step

                        const isExpected = item.step_type === EStepType.RESULT

                        // TODO: expectedStep.id => index.step
                        const currentExpectedId = item.index_step

                        const itemFormKey = getItemFormKey(itemIndex, 0)

                        const isActive = activeStep == itemFormKey
                        const isVisible = isActive || formValue?.[itemFormKey]?.status !== ERunStatus.UNTESTED

                        const initialValue = formValue[itemFormKey] || undefined
                        const initialStatus =
                            initialValue?.status === ERunStatus.PASSED ? initialValue : undefined

                        const value = initialStatus || formValue?.[itemFormKey]

                        const status = getRunStatusToIndicator(initialValue?.status)

                        const validationValues = get(item, 'validation_result', null)
                        const itemInitialValue = {
                            comment: isExpected ? validationValues?.reflection_description : item?.comment,
                            status: item?.status_step,
                            attachments: item.attachments
                        } as IManualStepValue

                        const handleChange = (status?: ERunStatus, info?: IEditCardInfo) => {
                            handleClick(
                                {
                                    index: itemIndex,
                                    status,
                                    info: {
                                        ...info,
                                        ...initialStatus
                                    },
                                    reflectionIndex: currentExpectedId,
                                    formKey: itemFormKey
                                }
                            )
                        }

                        const count = item?.part_num

                        const { titleComponent } = getFormattedStepInfo(item, {
                            fullValue: true,
                            isExpectedValue: isExpected
                        })

                        return <Steps.Step
                            key={ 'itemKey' }
                            className={ 'step-title-fullwidth' }
                            icon={
                                <StatusIndicator
                                    badgeStyle={ { display: 'inline' } }
                                    className={ 'step-indicator' }
                                    count={ count }
                                    isSharedStep={ isSharedStep({
                                        type: item.step_type,
                                        extra: item.extra
                                    }) }
                                    status={ status }
                                    type={ convertStepType(item.step_type, true) }
                                />
                            }
                            title={
                                <ManualEditCard
                                    disabled={ !isActive }
                                    enableCopyButton={ item?.step_type === EStepType.API }
                                    formDisabled={ !isActive }
                                    formVisible={ isVisible }
                                    initialValue={ itemInitialValue }
                                    label={ titleComponent }
                                    onChange={ handleChange }
                                    onFailed={ (info) => handleFailed({
                                        index: itemIndex,
                                        info,
                                        reflectionIndex: currentExpectedId
                                    }) }
                                    pending={ isPending && isActive }
                                    rawLabel={ item.original_step_description }
                                    resettable={ false }
                                    stepType={ item.step_type }
                                    value={ value?.status }
                                />
                            }
                        />
                    } }
                    run={ data }
                />


            </Flex>
        </Spin>
    )
}

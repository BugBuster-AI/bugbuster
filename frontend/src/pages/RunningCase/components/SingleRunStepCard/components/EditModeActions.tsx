import { CloseOutlined } from '@ant-design/icons';
import AiIcon from '@Assets/icons/ai-icon.svg?react'
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { replaceTemplateVariables } from '@Common/utils/variables';
import { IGetCoordinatesResponse } from '@Entities/common/models/get-coordinates.ts';
import { useCreateContextScreenshot, useGetCoordinates, useGetReflection } from '@Entities/common/queries/mutations.ts';
import { ERunStatus, IMedia, IRunStep } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ISingleRunStepCardProps } from '@Pages/RunningCase/components/SingleRunStepCard';
import { useSingleRunStepContext } from '@Pages/RunningCase/components/SingleRunStepCard/context';
import { useRunningStore } from '@Pages/RunningCase/store';
import { base64ToImageUrl } from '@Pages/RunningCase/utils';
import { Button, Flex, message, Space, Switch, Tooltip, Typography } from 'antd';
import { jsonrepair } from 'jsonrepair';
import find from 'lodash/find';
import get from 'lodash/get';
import isNil from 'lodash/isNil';
import isString from 'lodash/isString';
import values from 'lodash/values';
import { CSSProperties, MouseEvent, ReactNode, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { convertImageToBase64 } from '../../Content/components/DefaultDetails/components/EditClickAreaControls/utils';

const tryToGetErrorMsg = (msg?: string) => {
    if (!msg) return undefined
    try {
        return values(JSON.parse(jsonrepair(msg)))[0]
    } catch {
        return msg
    }
}

interface IProps {
    actionStyles?: CSSProperties
    actionName?: string | ReactNode;
    variablesList: Record<string, string>
    editActions?: ISingleRunStepCardProps['editActions']
}

const hasCoordinateError = (text: string) => {
    return text.includes('get_cordinates error');
}

export const EditModeActions = ({ actionStyles, variablesList, editActions, actionName }: IProps) => {
    const { t } = useTranslation();
    const {
        changeEditing,
        tempValue,
        setTempGeneratedData,
        stepItem,
        useSingleScreenshot,
        setUseSingleScreenshot
    } = useSingleRunStepContext()

    const { mutateAsync: getCoordinates, error: getCoordinatesError } = useGetCoordinates()
    const { mutateAsync: getReflection, error: getReflectionError } = useGetReflection()
    
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const removeEditingStep = useRunningStore((state) => state.removeEditingStep)
    const removeStepFromRun = useRunningStore((state) => state.removeStepFromRun)
    const updateEditingStep = useRunningStore((state) => state.updateEditingStep)
    const stepUUID = stepItem.localUUID!
    const editingStep = find(editingSteps, (item) => item.id === stepUUID)
    const editingStepItem = get(editingStep, 'step')
    const containerRef = useRef<HTMLDivElement | null>(null)
    const abortControllerRef = useRef<AbortController | null>(null)

    const isPending = get(editingStepItem, 'isLoading', false)

    const { mutateAsync: createContextScreenshot } = useCreateContextScreenshot()
    
    const isExpectedResult = stepItem?.step_type === EStepType.RESULT

    const valueIsEmpty = !tempValue || !tempValue.trim()

    const handleCheck = async () => {
        if (valueIsEmpty) {
            updateEditingStep(stepUUID, {
                error: 'Value is required',
                errorType: 'empty'
            })

            return
        }

        abortControllerRef.current?.abort()
        const controller = new AbortController()

        abortControllerRef.current = controller

        const baseUpdateData = {
            isLoading: true,
            error: undefined,
            editingClickArea: undefined,
        }

        // Для expected_result добавляем use_single_screenshot в extra, только если значение задано
        if (isExpectedResult && useSingleScreenshot !== undefined) {
            updateEditingStep(stepUUID, {
                ...baseUpdateData,
                extra: {
                    ...editingStepItem?.extra,
                    use_single_screenshot: useSingleScreenshot
                }
            })
        } else {
            updateEditingStep(stepUUID, baseUpdateData)
        }

        try {
            if (isExpectedResult) {
                const before = editingStepItem?.before
                const after = editingStepItem?.after

                // Формируем payload только с теми полями, которые действительно заданы
                const reflectionPayload: Record<string, unknown> = {
                    reflection_instruction: replaceTemplateVariables(tempValue, variablesList || {}),
                    before_minio_path: before,
                    after_minio_path: after,
                    signal: controller.signal,
                }

                // Добавляем use_single_screenshot только если оно задано
                if (useSingleScreenshot !== undefined) {
                    reflectionPayload.use_single_screenshot = useSingleScreenshot
                }

                const data = await getReflection(reflectionPayload)

                abortControllerRef.current = null

                const error = get(data, 'detail')

                if (error) {
                    const updateData: Record<string, unknown> = {
                        error,
                        checkResults: {
                            status: ERunStatus.FAILED,
                            title: 'Failed',
                            description: error
                        }
                    }
                    
                    // Добавляем use_single_screenshot в extra только если задано
                    if (useSingleScreenshot !== undefined) {
                        updateData.extra = {
                            ...editingStepItem?.extra,
                            use_single_screenshot: useSingleScreenshot
                        }
                    }
                    
                    updateEditingStep(stepUUID, updateData)

                    return
                }

                setTempGeneratedData(data as unknown as IGetCoordinatesResponse)

                if (!data) return
                
                const updateData = {
                    error: undefined,
                    errorType: undefined,
                    isLoading: false,
                    validation_result: {
                        reflection_time: data?.reflection_time,
                        reflection_thoughts: data?.reflection_thoughts,
                        reflection_description: data?.reflection_description,
                        reflection_title: data?.reflection_title,
                        reflection_step: data?.reflection_step,
                        reflection_result: data?.reflection_result,
                    }
                } as Partial<IRunStep>
                
                // Добавляем use_single_screenshot в extra только если задано
                if (useSingleScreenshot !== undefined) {
                    updateData.extra = {
                        ...editingStepItem?.extra,
                        use_single_screenshot: useSingleScreenshot
                    }
                }

                updateEditingStep(stepUUID, updateData)
                await editActions?.onCheck?.(data as unknown as IGetCoordinatesResponse)
                message.success(t('debug_mode.reflection_success'))
            } else {
                // === REGULAR STEP: использую get_coordinates ===
                const contextData = editingStepItem?.contextScreenshotMode
                const extraData = editingStepItem?.extra
                
                const isContextModeEnabled = editingStepItem?.contextScreenshotMode?.isEnabled;
                const hasScreenshot = !!extraData?.context_screenshot_path;
                const newCoordinates = editingStepItem?.contextScreenshotMode?.isNewCoordinates
                
                let contextScreenshot: IMedia | null = null;
                
                if (isContextModeEnabled) {
                    if (!contextData?.coordinates) {
                        contextScreenshot = extraData?.context_screenshot_path ?? null
                    } else if (hasScreenshot && !newCoordinates) {
                        contextScreenshot = extraData?.context_screenshot_path ?? null
                    } else {
                        try {
                            const originImage = await convertImageToBase64(editingStepItem?.before?.url ?? '')
                            const coordinates = contextData.coordinates

                            contextScreenshot = await createContextScreenshot({
                                image_base64_string: originImage,
                                x1: Math.floor(coordinates.x),
                                y1: Math.floor(coordinates.y),
                                x2: Math.floor(coordinates.x + coordinates.width),
                                y2: Math.floor(coordinates.y + coordinates.height),
                            })
        
                        } catch {
                            contextScreenshot = null
                            message.error('Failed to create context screenshot')
                        }
                    }
                }

                const data = await getCoordinates({
                    prompt: replaceTemplateVariables(tempValue, variablesList || {}),
                    minio_path: editingStepItem?.before,
                    signal: controller.signal,
                    context_screenshot_path: contextScreenshot ?? undefined
                })

                abortControllerRef.current = null

                const error = get(data, 'detail')

                if (error) {
                    if (!!error) {
                        const isCoordinateError = hasCoordinateError(error)

                        updateEditingStep(stepUUID, {
                            error,
                            checkResults: {
                                status: ERunStatus.FAILED,
                                title: 'Failed',
                                description: error
                            },
                            contextScreenshotMode: {
                                isNewCoordinates: isContextModeEnabled ? false 
                                    : editingStepItem?.contextScreenshotMode?.isNewCoordinates                        },
                            extra: {
                                context_screenshot_path: contextScreenshot ?? extraData?.context_screenshot_path
                            },
                            before_annotated_url: isCoordinateError
                                ? editingStepItem?.before
                                : editingStepItem?.before_annotated_url
                        })
                    }

                    return
                }

                setTempGeneratedData(data)

                if (!data) return

                const imageUrl = base64ToImageUrl(data.annotated_image_base64)
                
                updateEditingStep(stepUUID, {
                    error: undefined,
                    errorType: undefined,
                    contextScreenshotMode: {
                        isNewCoordinates: isContextModeEnabled ? false 
                            : editingStepItem?.contextScreenshotMode?.isNewCoordinates
                    },
                    extra: {
                        context_screenshot_path: contextScreenshot ?? extraData?.context_screenshot_path
                    },
                    checkResults: {
                        status: ERunStatus.PASSED,
                        description: data?.coords ? `Coordinates: ${data.coords.join(', ')}` : '',
                        title: data.generate_time || ''
                    },
                    isLoading: false,
                    before_annotated_url: {
                        url: imageUrl,
                        bucket: stepItem?.before_annotated_url.bucket,
                        file: stepItem?.before_annotated_url.file
                    }
                })
                await editActions?.onCheck?.(data)
                message.success(t('debug_mode.coordinates_success'))
            }
        } catch (e: unknown) {
            // Проверка на таймаут
            if ((e as {code?: string})?.code === 'ECONNABORTED' 
                || (e as {message?: string})?.message?.includes('timeout')) {
                updateEditingStep(stepUUID, {
                    error: t('debug_mode.timeout_error'),
                    checkResults: {
                        status: ERunStatus.FAILED,
                        title: 'Timeout',
                        description: t('debug_mode.timeout_error')
                    }
                })

                return
            }

            // Игнорируем отмену запроса
            if ((e as {name?: string})?.name === 'AbortError' 
                || (e as {message?: string})?.message === 'canceled' 
                || (e as {__CANCEL__?: boolean})?.__CANCEL__) {
                return
            }
        } finally {
            updateEditingStep(stepUUID, {
                isLoading: false
            })
        }
    }

    const onCancel = (e: MouseEvent<HTMLButtonElement>) => {
        e.stopPropagation()
        abortControllerRef.current?.abort()
        abortControllerRef.current = null
        
        try {
            // Если шаг был создан локально (вставлен вручную), удаляем его полностью
            if (stepItem.isLocalCreated) {
                removeStepFromRun(stepUUID)
            }
            
            removeEditingStep(stepUUID)
        } catch (e) {
            console.error(e)
        }

        editActions?.onCancel?.()
        changeEditing(false)
    }

    useEffect(() => {
        if (getCoordinatesError) {
            const name = (getCoordinatesError as {name?: string})?.name
            const msg = (getCoordinatesError as {message?: string})?.message

            if (name === 'AbortError' || msg === 'canceled') return

            const errorMessage =
                tryToGetErrorMsg(getErrorMessage({ error: getCoordinatesError, needConvertResponse: true }))

            updateEditingStep(stepUUID, {
                error: errorMessage,
                checkResults: {
                    status: ERunStatus.FAILED,
                    title: 'Failed',
                    description: errorMessage
                }
            })
        }
    }, [getCoordinatesError]);

    useEffect(() => {
        if (getReflectionError) {
            const name = (getReflectionError as {name?: string})?.name
            const msg = (getReflectionError as {message?: string})?.message

            if (name === 'AbortError' || msg === 'canceled') return

            const errorMessage =
                tryToGetErrorMsg(getErrorMessage({ error: getReflectionError, needConvertResponse: true }))

            updateEditingStep(stepUUID, {
                error: errorMessage,
                checkResults: {
                    status: ERunStatus.FAILED,
                    title: 'Failed',
                    description: errorMessage
                }
            })
        }
    }, [getReflectionError]);

    useEffect(() => {
        if (!containerRef.current) return

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onCancel(e as unknown as MouseEvent<HTMLButtonElement>)
            }
        }

        window.addEventListener('keydown', handleKeyDown)

        return () => {
            window.removeEventListener('keydown', handleKeyDown)
        }
    }, [])

    useEffect(() => {
        return () => {
            abortControllerRef.current?.abort()
            abortControllerRef.current = null
        }
    }, [])

    const beforeIsNil = isNil(editingStep?.step?.before)
    const canCheckStep = !beforeIsNil || stepItem?.isLocalCreated
    const checkDisabled = !tempValue || !canCheckStep

    const handleVerificationModeChange = (checked: boolean) => {
        setUseSingleScreenshot(checked)
        
        updateEditingStep(stepUUID, {
            extra: {
                ...stepItem.extra,
                use_single_screenshot: checked
            }
        })
    }

    const actionNameContent = () => {
        if (isExpectedResult) {
            let isChecked
            
            if (useSingleScreenshot === false) {
                isChecked = false
            } else {
                isChecked = true
            }
            // let checkedText = useSingleScreenshot == undefined ? 'None' : t('resultVerifications.state')

            return <Space
                direction="vertical"
                size="small"
            >
                <Flex
                    align="center"
                    gap={ 8 }
                    title={ isChecked ? t('resultVerifications.state') : t('resultVerifications.dynamic') }>
                    <Switch
                        checked={ isChecked }
                        checkedChildren={  t('resultVerifications.state') }
                        onChange={ handleVerificationModeChange }
                        unCheckedChildren={ t('resultVerifications.dynamic') }
                    />
                </Flex>
            </Space>
        }

        return actionName
            ? (
                <Typography.Text style={ { ...actionStyles } }>
                    {isString(actionName) ? actionName : actionName}
                </Typography.Text>
            )
            : <div/>
    }

    return (
        <div style={ { position: 'relative', width: '100%' } }>
            <Flex
                ref={ containerRef }
                align="center"
                gap={ 12 }

                justify="space-between"
                style={ { width: '100%', position: 'relative' } }
            >
                {actionNameContent()}

                <Flex align="center" gap={ 8 }>
                    <Tooltip title={ !canCheckStep ? 'AI feature is not available at this step' : undefined }>
                        <Button
                            disabled={ checkDisabled }
                            icon={ <AiIcon color={ 'white' }/> }
                            loading={ isPending }
                            onClick={ handleCheck }
                            size={ 'small' }
                            type={ 'primary' }
                            variant={ 'solid' }
                        >
                            Check
                        </Button>
                    </Tooltip>
                    <Button
                        color={ 'danger' }
                        icon={ <CloseOutlined/> }
                        onClick={ onCancel }
                        size={ 'small' }
                        variant={ 'solid' }
                    />
                </Flex>
            </Flex>
        
        </div>
    )
}

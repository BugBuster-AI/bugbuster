import { CopyOutlined } from '@ant-design/icons';
import AiIcon from '@Assets/icons/ai-icon.svg?react'
import { useThemeToken } from '@Common/hooks';
import { getErrorMessage } from '@Common/utils/getErrorMessage';
import { useDescribeElement } from '@Entities/common/queries/mutations';
import { ERunStatus } from '@Entities/runs/models';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Button, Flex, message, Switch, Typography } from 'antd'
import cn from 'classnames';
import get from 'lodash/get';
import { CSSProperties, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import styles from './EditClickAreaControls.module.scss'
import { convertImageToBase64 } from './utils';
import type { RelativeCoordinates } from '../ClickAreaCanvas/utils';
import { ContextScreenshotSwitch } from '../ContextScreenshotSwitch';

const defaultEditingClickAreaParams = {
    highlightColor: undefined as string | undefined,
    isThinkingMode: false,
    isLoading: false,
    error: '',
    coordinates: undefined as RelativeCoordinates | undefined
}

export const EditClickAreaControls = () => {
    const { t } = useTranslation();
    const selectedStep = useRunningStore((state) => state.selectedStep);
    const updateClickArea = useRunningStore((state) => state.updateEditingStep)
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const setGlobalLoader = useRunningStore((state) => state.setGlobalLoader)
    const token = useThemeToken()
    const selectedStepInEditing = editingSteps.find((item) => item.id === selectedStep?.id)
    const selectedStepData = selectedStepInEditing?.step
    const isEditingArea = selectedStepData?.editingClickArea
    const hasModelResponse = Boolean(selectedStepData?.editingClickArea?.hasResponse)
    
    const imageUrl = get(selectedStepData, 'before', null);
    
    const SELECTION_COLORS = useMemo(() => [token.colorError, token.colorPrimary, token.colorSuccess], [])
    
    const { mutateAsync: mutateClickAreaAsync } = useDescribeElement()

    if (!selectedStepInEditing) return null

    const selectedColor = selectedStepData?.editingClickArea?.highlightColor

    const startEditClickArea = () => {
        if (!selectedStepData) return
        
        updateClickArea(selectedStepInEditing?.id, {
            editingClickArea: { 
                ...defaultEditingClickAreaParams,
                highlightColor: token.colorError, 
                hasResponse: false
            },
            contextScreenshotMode: {
                isEnabled: false
            }
        })
    }

    const cancelEditClickArea = () => {
        if (!selectedStepData) return

        updateClickArea(selectedStepInEditing?.id,
            { 
                editingClickArea: undefined, 
                contextScreenshotMode: {
                    coordinates: undefined,
                    highlightColor: undefined
                }
            })
    }

    const toggleThinkingMode = (isThinkingMode: boolean) => {
        if (!selectedStepData || !selectedStepData.editingClickArea) return

        const updatedData = {
            editingClickArea: {
                isThinkingMode
            }
        }

        updateClickArea(selectedStepInEditing?.id, updatedData)
    }

    const clearSelection = () => {
        if (!selectedStepData || !selectedStepData.editingClickArea) return

        const updatedData = {
            editingClickArea: {
                coordinates: undefined
            }
        }

        updateClickArea(selectedStepInEditing?.id, updatedData)
    }

    const getDescription = async () => {
        if (!selectedStepData?.editingClickArea?.coordinates || !imageUrl) {
            return
        }

        try {
            updateClickArea(selectedStepInEditing?.id, {
                editingClickArea: {
                    hasResponse: false
                }
            })

            setGlobalLoader(true)

            const data = selectedStepInEditing.step?.editingClickArea

            const coordinates = data?.coordinates

            if (
                !coordinates ||
                !coordinates.x || 
                !imageUrl?.url || 
                !coordinates.y ||
                !coordinates.width ||
                !coordinates.height
            ) return

            const imageBase64 = await convertImageToBase64(imageUrl?.url);

            const response = await mutateClickAreaAsync({
                image_base64_string: imageBase64,
                x1: Math.floor(coordinates.x),
                y1: Math.floor(coordinates.y),
                x2: Math.floor(coordinates.x + coordinates.width),
                y2: Math.floor(coordinates.y + coordinates.height),
                thinking_mode: data?.isThinkingMode || false,
            })

            updateClickArea(selectedStepInEditing?.id, {
                editingClickArea: {
                    hasResponse: true
                },
                checkResults: {
                    status: ERunStatus.PASSED,
                    description: response.description,
                    time: response.generate_time,
                    title: t('running_page.click_area.element_description')
                },
                before_annotated_url: selectedStepData.before
            })
        } catch (error) {
            const errorMessage = getErrorMessage(
                { 
                    error: error as Error, 
                    needConvertResponse: true, 
                    defaultMessage: t('running_page.click_area.failed_to_get_description') 
                }
            )

            updateClickArea(selectedStepInEditing?.id, {
                before_annotated_url: selectedStepData.before,
                checkResults: {
                    time: undefined,
                    description: errorMessage!,
                    status: ERunStatus.FAILED
                }
            })
            message.error(errorMessage)
        } finally {
            setGlobalLoader(false)
        }
    }

    const handleCopyDescription = () => {
        if (!selectedStepData?.checkResults?.description) return

        navigator.clipboard.writeText(selectedStepData.checkResults.description)
        message.success(t('running_page.click_area.description_copied'))
    }

    const selectColor = (color: typeof SELECTION_COLORS[number]) => {
        if (!selectedStepData || !selectedStepData.editingClickArea) return

        const updatedData = {
            editingClickArea: {
                highlightColor: color
            }
        }

        updateClickArea(selectedStepInEditing?.id, updatedData)
    }

    const hasCoordinates = Boolean(selectedStepData?.editingClickArea?.coordinates);
    const extraData = selectedStepInEditing?.step?.extra
    const contextData = selectedStepInEditing?.step?.contextScreenshotMode
    const showContextSwitch = isEditingArea 
    || (extraData?.context_screenshot_path || extraData?.context_screenshot_used) || (contextData?.coordinates)

    return (
        <Flex className={ styles.outContainer } vertical>
            
            {!hasModelResponse && isEditingArea && (
                <Flex
                    align="flex-end"
                    className={ cn(styles.wrapper, styles.editing) }>
                    <Flex className={ styles.controls } gap={ 32 }>
                        <Flex gap={ 16 } vertical>
                            <Typography.Text type="secondary" strong>
                                {t('running_page.click_area.highlight_color')}
                            </Typography.Text>
                            <Flex gap={ 12 }>
                                {SELECTION_COLORS.map((color, index) => (
                                    <div 
                                        key={ `color-item-${index}` }
                                        className={
                                            cn(styles.colorItem, { [styles.selected]: selectedColor === color }) }
                                        onClick={ selectColor.bind(null, color) }
                                        style={ { '--selection-color': color } as CSSProperties }
                                    />
                                ))}
                            </Flex>
                        </Flex>

                        <Flex gap={ 16 } justify="space-between" vertical>
                            <Typography.Text type="secondary" strong>
                                {t('running_page.click_area.request_options')}
                            </Typography.Text>

                            <Flex gap={ 8 }>
                                <Switch onChange={ toggleThinkingMode } style={ { width: 'fit-content' } } />
                                <Typography.Text>{t('running_page.click_area.thinking_mode')}</Typography.Text>
                            </Flex>
                        </Flex>
                    </Flex>
                    <Flex className={ styles.buttons } gap={ 8 }>
                        <>
                            <Button
                                color="primary"
                                disabled={ !hasCoordinates }
                                icon={ <AiIcon color={ hasCoordinates ? 'white' : undefined } /> }
                                onClick={ getDescription }
                                variant="solid">
                                {t('running_page.click_area.get_description')}
                            </Button>
                            <Button 
                                color="red" 
                                disabled={ !hasCoordinates }
                                onClick={ clearSelection } 
                                variant="outlined">
                                {t('running_page.click_area.clear_selection')}
                            </Button>
                            <Button onClick={ cancelEditClickArea } variant="solid">
                                {t('running_page.click_area.cancel')}
                            </Button>
                        </>
                    </Flex>
                </Flex>
            )}
            <Flex className={ styles.bottomWrapper } gap={ 8 }>
                {(showContextSwitch) ? (
                    <ContextScreenshotSwitch wrapClassName={ styles.screenshotSwitch } />
                ) : <div />}

                <Flex className={ styles.bottomControlButtons } gap={ 8 }>
                    {hasModelResponse && 
                    (<Button color="green" icon={ <CopyOutlined /> } onClick={ handleCopyDescription } variant="solid">
                        {t('running_page.click_area.copy_description')}
                    </Button>

                    )}
                    {(!isEditingArea || hasModelResponse) && (
                        <Button color="orange" onClick={ startEditClickArea } variant="solid">
                            {t('running_page.click_area.define_element')}
                        </Button>
                    )}
                </Flex>
            </Flex>
        </Flex>
    )
}

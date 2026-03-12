import { AppearanceAnimation } from '@Common/components/Animations/Appearance'
import { useRunningStore } from '@Pages/RunningCase/store'
import { Flex, Switch, Tooltip, Typography } from 'antd'
import { SwitchProps } from 'antd/lib'
import  { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

interface IProps extends SwitchProps {
    wrapClassName?: string
}


export const ContextScreenshotSwitch = ({ wrapClassName, ...props }: IProps) => {
    const { t } = useTranslation()
    const TEXT = t('contextScreenshot.clarifyElement') 
    const TOOLTIP_DISABLED_TEXT = t('contextScreenshot.requireArea')
    const INFO_TEXT = t('contextScreenshot.info')
    const selectedStep = useRunningStore((state) => state.selectedStep)
    const updateEditingStep = useRunningStore((state) => state.updateEditingStep)
    const editingSteps = useRunningStore((state) => state.editingSteps)
    const selectedEditingStep = useRunningStore((state) => state.selectedEditingStep)
    const selectedEditingStepData = (editingSteps?.find((item) => item?.id === selectedStep?.id))?.step
    
    const stepContextData = selectedEditingStepData?.contextScreenshotMode
    const stepExtraData = selectedEditingStepData?.extra
    const stepClickAreaData = selectedEditingStepData?.editingClickArea

    const isEnabled = stepContextData?.isEnabled
    const isDisabled =
        !stepContextData?.coordinates 
        && !stepExtraData?.context_screenshot_path 
        && !isEnabled
    /*
     * const isDisabled = !selectedEditingStepData?.extra?.context_screenshot_path
     * координаты выбранной области
     */
    const editingClickAreaCoordinates = stepClickAreaData?.coordinates
    const highlightColor = stepClickAreaData?.highlightColor
    const handleChange = (checked: boolean) => {
        if (!selectedEditingStep) return

        updateEditingStep(selectedEditingStep.id, {
            contextScreenshotMode: {
                isEnabled: checked
            }
        })
    }
    
    useEffect(() => {
        if (!selectedEditingStep) return
        if (isDisabled) {
            updateEditingStep(selectedEditingStep.id, {
                contextScreenshotMode: {
                    isEnabled: false
                }
            })
        }
    }, [isDisabled])
     

    
    useEffect(() => {
        if (!selectedEditingStep || !selectedEditingStepData?.editingClickArea) return
     
        updateEditingStep(selectedEditingStep.id, {
            contextScreenshotMode: {
                coordinates: editingClickAreaCoordinates,
                isNewCoordinates: true,
                highlightColor
            }
        })
    }, [editingClickAreaCoordinates, highlightColor])
     


    return (
        <Flex className={ wrapClassName } vertical>
            <Flex gap={ 8 }>
                <Tooltip title={ isDisabled ? TOOLTIP_DISABLED_TEXT : '' }>
                    <Switch checked={ isEnabled } disabled={ isDisabled } onChange={ handleChange } { ...props } />
                </Tooltip>
                <Typography>{TEXT}</Typography>
            </Flex> 
            <AppearanceAnimation visible={ isEnabled }>
                <Typography style={ { marginTop: 8 } }>
                    {INFO_TEXT}
                </Typography>
            </AppearanceAnimation>
        </Flex>
    )
}

import { IStep } from '@Common/types'
import { ITempTestCaseFormSettings } from '@Entities/test-case/models'
import { Form, FormInstance, Typography } from 'antd'
import { FormItemProps } from 'antd/lib'
import { useTranslation } from 'react-i18next'
import { ContextScreenshotControl } from '../ContextScreenshotControl'
import styles from './StepFormItem.module.scss'

interface IProps extends FormItemProps {
    stepName: string | number | (string | number)[];
    form: FormInstance
    config?: ITempTestCaseFormSettings
    onConfigChange?: (config: ITempTestCaseFormSettings) => void
}
    
export const StepFormItem = ({ stepName, form, onConfigChange, children, config,...props }: IProps) => {
    const { t } = useTranslation()
    const stepItem = Form.useWatch(stepName, form) as IStep
    const needShowWarning = !config?.alreadyShowWarningContextScreenshots
     && !stepItem?.tempFormData?.isDeleteContextScreenshot

    const handleScreenshotClick = () => {
        const currentStepItem = form.getFieldValue(stepName) as IStep
        
        if (!config?.alreadyShowWarningContextScreenshots) {
            onConfigChange?.({
                alreadyShowWarningContextScreenshots: true
            })
        }

        if (currentStepItem?.tempFormData?.isDeleteContextScreenshot) {
            form.setFieldValue(stepName, {
                ...currentStepItem,
                tempFormData: {
                    ...currentStepItem.tempFormData,
                    isDeleteContextScreenshot: false,
                }
            })

            return
        }

        form.setFieldValue(stepName, {
            ...currentStepItem,
            tempFormData: {
                ...currentStepItem.tempFormData,
                isDeleteContextScreenshot: true,
            }
        })
    }


    const getCaption = () => {
        const extraData = stepItem?.extraData

        if (extraData?.use_single_screenshot  === true) {
            return t('resultVerifications.state')
        }
        
        if (extraData?.use_single_screenshot === false) {
            return (t('resultVerifications.dynamic'))
        }

        return null
    }

    const caption = getCaption()

    return (
        <div className={ styles.wrapper }>
            <Form.Item className={ 'no-errors-margin extra-warning width-100' } { ...props }>
                {children}
            </Form.Item>
            {!!caption && <Typography.Text type="secondary">{caption}</Typography.Text>}
            {stepItem?.extraData?.context_screenshot_used && (
                <div className={ styles.contextControl }>
                    <ContextScreenshotControl
                        isDeleted={ stepItem.tempFormData?.isDeleteContextScreenshot }
                        needShowModal={ needShowWarning }
                        onClick={ handleScreenshotClick }
                        screenshotUrl={ stepItem?.extraData?.context_screenshot_path?.url }
                    />
                </div>
            )}
        </div>
    )
}

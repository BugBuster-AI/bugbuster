import { CloseOutlined } from '@ant-design/icons';
import { CASE_SAVE_ERROR_TEMPLATE, STEP_ERROR_TEMPLATE } from '@Common/consts/autofaqBotTemplates.ts';
import { IApiErrorDetail, IError, IStep } from '@Common/types';
import { sendUserFaqMessage } from '@Common/utils/autofaqBot.ts';
import { transformStepsForError } from '@Common/utils/transformStepsForError.ts';
import { EStepGroup } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ITestCaseStep } from '@Entities/test-case/models';
import { FormInstance, message, Modal } from 'antd';
import parse from 'html-react-parser';
import { jsonrepair } from 'jsonrepair';
import entries from 'lodash/entries';
import forEach from 'lodash/forEach';
import get from 'lodash/get';
import isObject from 'lodash/isObject';
import size from 'lodash/size';
import { removeSlashes } from 'slashes';

const clearValue = (value?: string) => {
    if (!value) {
        return ''
    }

    return removeSlashes(value.replace(/\\\n/g, '\n'))
}

export const getStepApiData = (step: ITestCaseStep): IStep['apiData'] | undefined => {
    if (step.type === EStepType.API) {
        if (!step.url && !step.method) {
            return undefined
        }

        return {
            data: step.data,
            url: step.url,
            files: step.files,
            headers: step.headers,
            method: step.method
        }
    }

    return undefined
}

export const localStepToHttp = (step: IStep): ITestCaseStep => {
    const extra = {
        ...step.extraData
    }

    // удаляем скриншот из extra, если в форме указано удалить его
    if (step.tempFormData?.isDeleteContextScreenshot) {
        extra.context_screenshot_path = null
        delete extra.context_screenshot_used
    }

    return {
        value: clearValue(step.step),
        type: step.type!,
        extra,
        ...step.apiData
    }
}

export const httpStepToLocal = (step: ITestCaseStep, index: number, data?: any, stepGroup?: EStepGroup): IStep => {
    return {
        step: get(step, 'value', step as unknown as string),
        type: get(step, 'type', EStepType.STEP),
        localIndex: index,
        data,
        extraData: get(step, 'extra'),
        apiData: getStepApiData(step),
        stepGroup,
        tempFormData: {}
    }
}

interface IFormErrorHandlerProps {
    error: IApiErrorDetail | IError
    form: FormInstance
    t: (v: string) => string
}

export const formServerErrorHandler = ({ form, t, error }: IFormErrorHandlerProps) => {
    const details = error.detail

    if (typeof details === 'string') {
        try {

            const cleanedDetail = jsonrepair(details)

            const parsedData = JSON.parse(cleanedDetail)

            if (!isObject(parsedData)) {
                throw new Error('the parsed data is a string, expected an object or array');
            }

            const formValues = form.getFieldsValue()

            const parsedEntries = entries(parsedData)

            const transformedStepsArray = transformStepsForError(formValues)
            let scrolled = false

            forEach(parsedEntries, (value, index) => {
                const [key, val] = value

                if (isNaN(+key)) {
                    throw new Error('the key is not a number, expected a numeric index');
                }

                const step = transformedStepsArray?.[Number(key)]

                if (step?.stepGroup) {
                    const name = [step?.stepGroup, Number(step.localIndex), 'step']

                    if (index === 0) {
                        const inputValue = form.getFieldValue(name)

                        sendUserFaqMessage(STEP_ERROR_TEMPLATE({ step: inputValue, error: val as string }))
                    }

                    setTimeout(() => {
                        if (!scrolled) {
                            form.scrollToField(name, {
                                behavior: 'smooth',
                                block: 'center'
                            })
                            scrolled = true
                        }

                        form.setFields([
                            {
                                name,
                                errors: [val as string]
                            }
                        ])
                    }, 20)
                }
            })

            if (size(parsedEntries) > 0) {
                Modal.info({
                    centered: true,
                    destroyOnClose: true,
                    icon: null,
                    closable: true,
                    maskClosable: true,
                    closeIcon: <CloseOutlined/>,
                    title: t('validation_error.title'),
                    content: parse(t('validation_error.text'))
                })
            }


        } catch (e) {
            console.error('error parsing', e)

            sendUserFaqMessage(CASE_SAVE_ERROR_TEMPLATE({ error: details }))
            message.error(details || t('messages.error.update.test_case'))
        }

        return
    }

    return;
}


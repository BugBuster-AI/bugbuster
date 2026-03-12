import { CloseOutlined } from '@ant-design/icons';
import { CASE_SAVE_ERROR_TEMPLATE, STEP_ERROR_TEMPLATE } from '@Common/consts/autofaqBotTemplates.ts';
import { IApiErrorDetail, IError } from '@Common/types';
import { sendUserFaqMessage } from '@Common/utils/autofaqBot.ts';
import { prepareForEdit, prepareForSubmit } from '@Common/utils/test-case/prepares.ts';
import { transformStepsForError } from '@Common/utils/transformStepsForError.ts';
import { IBaseForm } from '@Entities/test-case/components/Form/models';
import { ITestCase } from '@Entities/test-case/models';
import { FormInstance, message, Modal } from 'antd';
import parse from 'html-react-parser';
import { jsonrepair } from 'jsonrepair';
import entries from 'lodash/entries';
import forEach from 'lodash/forEach';
import isObject from 'lodash/isObject';
import size from 'lodash/size';

export const transformUpdatedCaseData = <T extends IBaseForm>(data: T) => {
    return prepareForSubmit(data)
};


export const reverseTransformCaseData = (data?: ITestCase) => {
    if (!data) return null

    return prepareForEdit(data)
};

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

                            const domId = name.join('_')

                            document.getElementById(domId)?.scrollIntoView({
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

    try {

        const errorField = details[0].loc.slice(-1)[0]
        
        form.setFields([
            { name: errorField, errors: [details[0].msg] }
        ])
        
        form.scrollToField(errorField, { behavior: 'smooth', block: 'center' })
    } catch {
        message.error(details[0].msg || t('messages.error.update.test_case'))
    }

    return;
}

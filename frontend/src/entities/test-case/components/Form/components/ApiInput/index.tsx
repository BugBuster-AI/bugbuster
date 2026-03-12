import { SettingOutlined } from '@ant-design/icons';
import { isUrl } from '@ant-design/pro-components';
import { METHOD_COLORS } from '@Common/consts/common.ts'
import { CLASSNAMES } from '@Common/consts/css.ts';
import { IStep } from '@Common/types';
import { Logger } from '@Common/utils/logger/log.ts';
import { HighlightTextarea } from '@Components/HighlightTextarea';
import { CurlEditModal } from '@Entities/test-case/components/Form/components';
import { ApiInputContext, useApiInputContext } from '@Entities/test-case/components/Form/components/ApiInput/context';
import { CurlValidationError } from '@Entities/test-case/components/Form/components/ApiInput/errors.ts';
import {
    apiDataToCurlObj,
    formatCurlAsync, transformJsonToCurl,
} from '@Entities/test-case/components/Form/components/ApiInput/helper.ts';
import { ICurlObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';
import { Button, Flex, FormInstance } from 'antd';
import cn from 'classnames';
import isEmpty from 'lodash/isEmpty';
import { CSSProperties, InputHTMLAttributes, useEffect, useMemo, useState } from 'react';
import { removeSlashes } from 'slashes';
import styles from './ApiInput.module.scss'

interface IProps {
    form: FormInstance
    baseName: unknown[]
    style?: CSSProperties
    getRules: (rules: any[]) => void
    variablesList?: string[]
}

const NULL_EXTRA = {
    set_variables: {},
    validations: []
} as IStep['extraData']

export const ApiInputInner = ({ baseName, style, getRules, form, variablesList, ...inputProps }: IProps) => {
    const props = inputProps as InputHTMLAttributes<HTMLInputElement>
    // const { t } = useTranslation()
    const [visibleValue, setVisibleValue] = useState('')
    const [disabled, setDisabled] = useState(false)

    const openFormBtnDisabled = !!(!disabled && visibleValue)
    const {
        setCurlString,
        setCurlObj,
        setOriginCurlString,
        curlString: curlStringContext,
        curlObj: curlObjContext,
        setExtra,
        extra
    } = useApiInputContext()

    const inputName = [...baseName, 'step']
    const inputData = form.getFieldValue(baseName) as IStep

    const stringValue = inputData.step
    const extraData = inputData?.extraData

    const [openForm, setOpenForm] = useState(false)

    const handleCloseModal = () => {
        setOpenForm(false)
    }

    const handleVisibleValueChange = (value) => {
        setVisibleValue(value)
    }

    const handleOpenModal = () => {
        if (openFormBtnDisabled) {
            return
        }
        setOpenForm(true)
    }

    const handleOpenModalFromInput = () => {
        if (!disabled) {
            return
        }

        setOpenForm(true)
    }

    const handleUpdateInput = async (value: string, apiData?: IStep['apiData']) => {
        if (disabled) {
            return
        }
        try {
            let curlString = ''
            let curlObj = {} as ICurlObject

            if (!isEmpty(apiData) && !!apiData) {

                // Если передали apiData, то используем его
                curlObj = apiDataToCurlObj(apiData)
                curlString = await transformJsonToCurl(apiData)
            } else {
                // Если не передали apiData, то парсим курл
                const { string: curlStr, obj } = await formatCurlAsync(value) || {}

                curlObj = obj
                curlString = curlStr
            }

            if (curlObj.url) {
                setVisibleValue(curlObj.url || '')
            }

            setCurlObj(curlObj)
            setCurlString(curlString)
            setOriginCurlString(value)
            setDisabled(true)
        } catch (e) {
            console.error(e)
            const error = e as CurlValidationError

            setVisibleValue(value)

            setTimeout(() => {
                form.setFields([{
                    name: inputName,
                    value,
                    errors: [error?.message || 'Incorrect curl string' as string]
                }])
            })
        }
    }

    const handleBlurInput = async () => {
        const apiData = inputData?.apiData

        await handleUpdateInput(visibleValue, apiData)
    }

    // Функция валидации значений инпута
    const validateInput = async (name: string, value: string) => {
        const nameArray = name.split('.')
        const currentBaseName = nameArray.slice(0, -1)
        const currentInputData = form.getFieldValue(currentBaseName)

        const currentApiData = currentInputData?.apiData as IStep['apiData']

        if (!currentApiData?.url && !currentApiData?.method) {
            await formatCurlAsync(removeSlashes(value))
        }

        if (!isUrl(currentApiData?.url)) {
            throw new CurlValidationError('Invalid or missing URL', value)
        }
    }

    // устанавливаем правила валидации для api инпута
    useEffect(() => {
        const rules = [
            {
                validator: (state, value) => {
                    return new Promise(async (resolve, reject) => {
                        try {
                            await validateInput(state.field, value)

                            resolve('ok')
                        } catch (e) {
                            const error = e as CurlValidationError

                            reject(error.message as string)
                        }
                    });
                }
            }
        ]

        if (getRules) {
            getRules(rules)
        }
    }, []);


    // синхронизация контекста с формой КЕЙСА
    useEffect(() => {
        if (curlStringContext && curlObjContext) {
            form.setFieldValue(inputName, curlStringContext)
        }
    }, [curlObjContext, curlStringContext]);

    // синхронизация extraData из формы КЕЙСА в контекст
    useEffect(() => {
        if (extraData) {
            setExtra(extraData)
        }
    }, [extraData]);

    // синхронизация контекста в форму КЕЙСА
    useEffect(() => {
        const syncContext = async () => {
            Logger.log('SYNC CONTEXT TRIGGERED', { curlObjContext, extra })
            const str = await transformJsonToCurl(curlObjContext)

            setVisibleValue(curlObjContext.url || '')

            const apiData = {
                headers: curlObjContext.headers,
                data: curlObjContext.data,
                method: curlObjContext.method || 'GET',
                url: curlObjContext.url || '',
                files: curlObjContext.files,
            } as IStep['apiData']

            form.setFieldValue([...baseName, 'step'], str)
            form.setFieldValue([...baseName, 'extraData'], extra || NULL_EXTRA)
            form.setFieldValue([...baseName, 'apiData'], apiData)
        }

        if (!isEmpty(curlObjContext)) {
            syncContext()
        }

    }, [extra, curlObjContext]);

    // инициализация значения из формы КЕЙСА
    useEffect(() => {
        const initValue = stringValue
        const apiData = inputData?.apiData

        if (initValue) {

            Logger.log('HANDLE UPDATE INPUT TRIGGERED', { initValue, apiData, stringValue, curlObjContext })
            handleUpdateInput(initValue as string, apiData)

            return
        }
    }, [stringValue, curlObjContext, curlStringContext]);

    return (
        <>
            <CurlEditModal onClose={ handleCloseModal } open={ openForm }/>
            <Flex style={ { ...style } }>
                {curlObjContext?.method &&
                    <div
                        onClick={ handleOpenModal }
                        style={ {
                            cursor: 'pointer',
                            marginInline: `4px 8px`,
                            paddingTop: 4,
                            width: 60,
                            minWidth: 60,
                            fontWeight: 700,
                            color: METHOD_COLORS[curlObjContext.method]
                        } }>
                        {curlObjContext.method}
                    </div>
                }
                <HighlightTextarea
                    className={ cn(styles.textarea, CLASSNAMES.textareaWithVariables, { [styles.disabled]: disabled }) }
                    disabled={ disabled }
                    initialVariables={ variablesList || [] }
                    onBlur={ handleBlurInput }
                    onChange={ handleVisibleValueChange }
                    onClick={ handleOpenModalFromInput }
                    placeholder={
                        'curl...'
                        // t(`create_test_case.placeholders.${EStepType.API}`)
                    }
                    value={ visibleValue }
                />
                <Button
                    disabled={ openFormBtnDisabled }
                    icon={ <SettingOutlined/> }
                    onClick={ handleOpenModal }
                    style={ { marginLeft: 8 } }
                    type={ 'text' }
                    variant={ 'text' }
                />
                <input style={ { position: 'absolute', visibility: 'hidden', opacity: 0 } } { ...props }/>
            </Flex>
        </>
    )
}
export const ApiInput = (props: IProps) => {
    const { form, baseName } = props || {}
    const [curlObj, setCurlObj] = useState({})
    const [curlString, setCurlString] = useState('')
    const [originCurlString, setOriginCurlString] = useState('')
    const [extra, setExtra] = useState<IExtraCaseType | null>(null)
    const inputData = form.getFieldValue(baseName) as IStep
    const [stepData, setStepData] = useState<IStep>(inputData)

    const memoizedContextValue = useMemo(() => ({
        curlString,
        curlObj,
        extra,
        setExtra,
        setCurlString,
        setCurlObj,
        originCurlString,
        setOriginCurlString,
        setStepData,
        stepData
    }), [curlObj, curlString, originCurlString, extra, stepData])

    return (
        <ApiInputContext.Provider value={ memoizedContextValue }>
            <ApiInputInner { ...props } />
        </ApiInputContext.Provider>
    )
}

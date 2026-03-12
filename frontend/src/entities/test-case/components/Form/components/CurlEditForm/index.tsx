import { API_METHODS, METHOD_COLORS } from '@Common/consts/common';
import { getBodyTypeFromContentType, getCurlMode, RAW_BODY_CONTENT_TYPES } from '@Common/utils';
import { Logger } from '@Common/utils/logger/log.ts';
import { useApiInputContext } from '@Entities/test-case/components/Form/components/ApiInput/context';
import { ICurlObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import { CurlEditFormContext, IBodyState } from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import {
    objToMapParams,
    parseUrlWithoutSort,
    prepareFormForObj,
    prepareValidations,
    prepareVariables
} from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import {
    IFormDataItem,
    IHeaderEdit, IInitialData,
    IParamEdit,
    IValidationEdit, IVariableEdit
} from '@Entities/test-case/components/Form/components/CurlEditForm/models.ts';
import { Button, Flex, Form, Input, message, Modal, Select } from 'antd';
import cn from 'classnames';
import get from 'lodash/get';
import includes from 'lodash/includes';
import isEmpty from 'lodash/isEmpty';
import isString from 'lodash/isString';
import map from 'lodash/map';
import merge from 'lodash/merge';
import qs from 'query-string'
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FormBody } from './components';
import styles from './CurlEditForm.module.scss'

interface IModalProps {
    open: boolean
    onClose: () => void
}

export const CurlEditForm = ({ onClose }: IModalProps) => {
    const { t } = useTranslation()

    const {
        curlString,
        curlObj,
        extra,
        setExtra,
        setCurlObj,
    } = useApiInputContext()
    const [form] = Form.useForm()

    const [method, setMethod] = useState<string>(curlObj?.method || 'GET')

    const [url, setUrl] = useState('')
    const [params, setParams] = useState<IParamEdit[]>([])
    const [headers, setHeaders] = useState<IHeaderEdit[]>([])
    const [body, setBody] = useState<IBodyState>({
        currentBodyType: 'none'
    })
    const [validation, setValidation] = useState<IValidationEdit[]>([])
    const [variables, setVariables] = useState<IVariableEdit[]>([])
    const [sourceData, setSourceData] = useState<IInitialData>()
    const [activeTab, setActiveTab] = useState('1')

    const urlFormValue = Form.useWatch('url', form)

    // guards to prevent feedback loops between effects
    const syncingFromUrlRef = useRef(false)
    const syncingFromParamsRef = useRef(false)

    const handleSetBody = (bodyData: Partial<IBodyState>) => {
        setBody((prev) => {
            return merge({}, prev, bodyData)
        })
    }

    // normalize helpers
    const normalizeParams = (arr: IParamEdit[]) =>
        arr
            .filter((p) => String(p.key || '').length > 0)
            .reduce((acc, p) => {
                acc[String(p.key)] = String(p.value ?? '')

                return acc
            }, {} as Record<string, string>)

    const stringifySorted = (obj: Record<string, unknown>) =>
        qs.stringify(obj, { sort: false })

    const formData = {
        params,
        headers,
        body,
        validation,
        variables,
        sourceData,
        url,
        method
    }

    // мемоизация контекста, чтобы не пересоздавать его каждый рендер

    const memoizedContextValue = useMemo(() => ({
        activeTab,
        formData,
        setMethod,
        setUrl,
        setBody: handleSetBody,
        setParams,
        setHeaders,
        setValidation,
        setVariables,
        setActiveTab
    }), [body, headers, params, validation, variables, activeTab, sourceData, url, method])

    const selectBefore = (
        <Select
            className={ cn(styles.methodSelect) }
            defaultValue={ method }
            onChange={ setMethod }
            //@ts-ignore
            style={ { '--selection-color': METHOD_COLORS[method] } }
        >
            {map(API_METHODS, (item) => (
                <Select.Option key={ item } style={ { color: METHOD_COLORS[item], fontWeight: 700 } } value={ item }>
                    {item}
                </Select.Option>
            ))}
        </Select>
    )

    // сохранение формы
    const handleSave = async () => {

        try {
            await form.validateFields()

            Logger.log(formData, 'FORM DATA')
            const objData = prepareFormForObj(formData)

            Logger.log(objData, 'OBJ DATA!!!')

            setCurlObj({ ...objData.obj } as ICurlObject)
            setExtra({
                validations: objData.validation,
                set_variables: objData.variables
            })

            onClose()
            message.success(t('apiForm.messages.saved'))
        } catch {
            message.error(t('apiForm.messages.validationError'))
        }
    }


    // Первичная инициализация формы из curlObj при открытии
    useEffect(() => {
        const curlObj = sourceData?.curlObj

        Logger.log(sourceData?.curlString, 'ORIGINAL CURL')
        if (curlObj) {
            const { headers, method, data, contentType, files, url: initialUrl, params } = curlObj || {}

            const { query } = parseUrlWithoutSort(initialUrl || '')

            setUrl(initialUrl || '')

            if (params) {
                setParams(objToMapParams(params))
            } else {
                setParams(query)
            }

            const curlMode = getCurlMode(contentType, data)

            Logger.log(curlMode, 'CURL MODE')

            const bodyState = {
                'currentBodyType': curlMode
            } as IBodyState

            if (!isEmpty(data) || !isEmpty(files)) {
                Logger.log(curlObj, 'INITIAL OBJ')
                switch (curlMode) {
                    case 'formData':
                        const arrForm = data ? map(objToMapParams(data), (el) => ({
                            ...el,
                            type: 'text'
                        } as IFormDataItem)) : []
                        const arrFiles = files ? map(objToMapParams(files), (el) => ({
                            ...el,
                            type: 'file'
                        } as IFormDataItem)) : []

                        bodyState['formData'] = [...arrForm, ...arrFiles]
                        Logger.log(bodyState, 'FORM_DATA')
                        break


                    case 'urlEncoded':
                        const arrData = data ? objToMapParams(data) : []

                        bodyState['urlEncoded'] = arrData

                        break

                    case 'raw':
                        if (includes(RAW_BODY_CONTENT_TYPES, contentType)) {
                            Logger.log(data, 'DATA')
                            bodyState['raw'] = {
                                value: isString(data) ? data : JSON.stringify(data, undefined, 4),
                                type: getBodyTypeFromContentType(contentType) || 'json'
                            }
                        } else {
                            // если не определен data-type - то исходит от типа data
                            let dataType

                            if (isString(data)) {
                                dataType = 'text'
                            } else if (isEmpty(data)) {
                                dataType = 'text'
                            } else if (isString(data)) {
                                dataType = 'text'
                            } else {
                                dataType = 'json'
                            }
                            const defaultData = isString(data) ? data : JSON.stringify(data, undefined, 4)

                            bodyState['raw'] = {
                                value: defaultData,
                                type: dataType
                            }
                        }

                        break
                    default: {
                        const defaultData = isString(data) ? data : JSON.stringify(data, undefined, 4)

                        bodyState[curlMode] = defaultData
                    }
                }
            } else if (isEmpty(data) && isEmpty(files)) {
                bodyState['currentBodyType'] = 'none'
            }

            Logger.log(headers, 'HEADERS')

            // трансформация хедеров из объекта в массив
            const transformedHeaders = headers ? objToMapParams(headers) : []

            setHeaders(transformedHeaders)
            setMethod(method || 'GET')

            handleSetBody(bodyState)

            const validations = get(sourceData, 'extra.validations')
            const variables = get(sourceData, 'extra.set_variables')

            setValidation(prepareValidations(validations))
            setVariables(prepareVariables(variables))
        }
    }, [sourceData]);

    // URL -> Params sync
    useEffect(() => {
        const { query } = parseUrlWithoutSort(urlFormValue || '')

        const nextParams = query

        if (syncingFromParamsRef.current) {
            syncingFromParamsRef.current = false

            return
        }

        const currentSig = stringifySorted(normalizeParams(params))
        const nextSig = stringifySorted(normalizeParams(nextParams))

        if (currentSig !== nextSig) {
            syncingFromUrlRef.current = true
            setParams(nextParams)
        }
    }, [urlFormValue])

    // Установка sourceData при изменении curlObj или curlString (обычно инициализация)
    useEffect(() => {
        if (curlObj && curlString) {
            setSourceData({
                curlObj,
                curlString,
                extra: extra || null
            })
        }
    }, [])
    // }, [curlObj, curlString, extra]);


    // чтобы не было циклов при синхронизации URL и Params
    useEffect(() => {
        if (syncingFromParamsRef.current) {
            syncingFromParamsRef.current = false

            return
        }
        form.setFieldValue('url', url)
    }, [url]);

    useEffect(() => {
        if (!urlFormValue || urlFormValue === url) {

            return
        }
        setUrl(urlFormValue)
    }, [urlFormValue]);

    return (
        <CurlEditFormContext.Provider value={ memoizedContextValue }>
            <Flex gap={ 24 } style={ { paddingBlock: 12 } } vertical>
                <Form form={ form }>
                    <Form.Item
                        name={ 'url' }
                        rules={ [
                            {
                                required: true,
                                message: t('errors.input.required')
                            },
                            /*
                             * {
                             *     type: 'url',
                             *     message: t('errors.input.url')
                             * },
                             */
                        ] }
                    >
                        <Input
                            addonBefore={ selectBefore }
                            className={ styles.input }
                            placeholder={ t('apiForm.url') }
                        />
                    </Form.Item>
                    <FormBody/>
                </Form>
            </Flex>
            <Flex gap={ 8 } justify={ 'flex-end' }>
                <Button onClick={ onClose } type={ 'default' }>{t('apiForm.cancel')}</Button>
                <Button onClick={ handleSave } type={ 'primary' }>{t('apiForm.ok')}</Button>
            </Flex>
        </CurlEditFormContext.Provider>
    )
}

export const CurlEditModal = ({ ...props }: IModalProps) => {
    const { t } = useTranslation()
    const { open, onClose } = props || {}

    return (
        <Modal
            footer={ null }
            height={ '60%' }
            onCancel={ onClose }
            open={ open }
            title={ t('apiForm.title') }
            width={ 1280 }
            centered
            closable
            destroyOnClose
            maskClosable
        >
            {open && <CurlEditForm { ...props } />}
        </Modal>
    )
}

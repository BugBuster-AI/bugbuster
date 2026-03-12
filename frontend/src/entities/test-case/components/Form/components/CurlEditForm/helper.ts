import { nanoid } from '@ant-design/pro-components';
import { EContentType, getContentTypeFromMode } from '@Common/utils';
import { Logger } from '@Common/utils/logger/log.ts';
import { ICurlObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import { IFormState } from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import {
    IParamEdit,
    IValidationEdit,
    IVariableEdit
} from '@Entities/test-case/components/Form/components/CurlEditForm/models.ts';
import { IValidationType, SetVariables } from '@Entities/test-case/models/test-case-variables.ts';
import { jsonrepair } from 'jsonrepair';
import entries from 'lodash/entries';
import get from 'lodash/get';
import isEmpty from 'lodash/isEmpty';
import isString from 'lodash/isString';
import map from 'lodash/map';
import reduce from 'lodash/reduce';

export const addNanoid = (arr: object[], key?: string) => {
    return map(arr, (item) => {
        return {
            ...item,
            [key || 'id']: nanoid(),
        }
    })
}

export const prepareValidations = (data?: IValidationType[]): IValidationEdit[] => {
    if (!data) {
        return []
    }

    return map(data, (item) => ({
        type: item.validation_type,
        target: item.target,
        expectedValue: item.expected_value
    } as IValidationEdit))
}

export const prepareVariables = (data?: SetVariables): IVariableEdit[] => {
    if (!data || isEmpty(data)) {
        return []
    }

    return map(entries(data), ([key, value]) => ({
        name: key,
        path: value
    } as IVariableEdit))
}

export const getJsonBody = (val?: string) => {
    if (!val) return undefined
    try {
        return JSON.parse(jsonrepair(val))
    } catch {
        return {}
    }
}

/*
 *
 * export const prepareDataForServer = (data: IFormState, prevStepData: IStep) => {
 *     const { headers, body, url, params, method } = data || {}
 *
 *     const variables = reduce(data.variables, (acc, item) => {
 *         acc[item.name] = item.path
 *
 *         return acc
 *     }, {} as SetVariables)
 *
 *     const validations = map(data.validation, (item) => ({
 *         target: item.target,
 *         validation_type: item.type,
 *         expected_value: item.expectedValue
 *     } as IValidationType))
 *
 *     const preparedHeaders = reduce(headers, (acc, val) => {
 *         acc[val.key] = val.value
 *
 *         return acc
 *     }, {})
 *
 *     const preparedParams = reduce(params, (acc, val) => {
 *         acc[val.key] = val.value
 *
 *         return acc
 *     }, {})
 *
 *     const preparedBody = getJsonBody(body)
 *
 *     // на всякий случай ощищаем от параметров
 *     const { url: clearedUrl } = qs.parseUrl(url)
 *     const curlValue = transformJsonToCurl({
 *         url: clearedUrl,
 *         params: preparedParams,
 *         headers: preparedHeaders,
 *         body: preparedBody,
 *         method,
 *     })
 *
 *     return {
 *         ...prevStepData,
 *         extraData: {
 *             set_variables: variables,
 *             validations
 *         } as IExtraCaseType,
 *         step: curlValue,
 *     } as IStep
 * }
 */


// Функция для подготовки объекта из формы КУРЛА в формат curlObj
export const prepareFormForObj = (data: IFormState): {
    obj: ICurlObject,
    validation: IValidationType[],
    variables: SetVariables,
} => {
    const { headers, body, url, params, method } = data || {}
    const contentType = getContentTypeFromMode(get(data, 'body.currentBodyType'), get(data, 'body.raw.type'))

    const preparedHeaders = reduce(headers, (acc, val) => {
        acc[val.key] = val.value

        return acc
    }, {})

    Logger.log(preparedHeaders, 'PREPARED HEADERS')

    const currentBodyType = get(data, 'body.currentBodyType')


    if (contentType && currentBodyType !== 'none') {
        /*
         * Проверяем, установлен ли вообще Content Type в хедерах
         * const originalHeadersContentType = getContentType(preparedHeaders, false)
         *
         * if (originalHeadersContentType) {
         *     // Установка изменившегося Content Type
         *     preparedHeaders['Content-Type'] = contentType
         * }
         */
    }

    /*
     * if (currentBodyType === 'none') {
     *     // Удаление Content Type если тело отключено
     *     delete preparedHeaders['Content-Type']
     * }
     */

    const preparedParams = reduce(params, (acc, val) => {
        acc[val.key] = val.value

        return acc
    }, {})

    const variables = reduce(data.variables, (acc, item) => {
        acc[item.name] = item.path

        return acc
    }, {} as SetVariables)


    const validation = map(data.validation, (item) => ({
        target: item.target,
        validation_type: item.type,
        expected_value: item.expectedValue
    } as IValidationType))

    // Подготовка файлов из formData
    let preparedFiles = {}
    let preparedData = {}

    // Подготовка данных из formData или urlEncoded
    switch (body?.currentBodyType) {
        case 'urlEncoded':
            preparedData = reduce(body?.urlEncoded, (acc, item) => {
                acc[item.key] = item.value

                return acc
            }, {})
            break
        case 'formData':
            preparedData = reduce(body?.formData, (acc, item) => {
                if (item.type === 'file') {
                    preparedFiles[item.key] = item.value
                } else if (item.type === 'text') {
                    acc[item.key] = item.value
                }

                return acc
            }, {})
            break
        case 'raw':
            if (contentType !== EContentType.APPLICATION_JSON) {
                preparedData = body?.raw?.value || ''
                break
            }
            preparedData = getJsonBody(body?.raw?.value)
            break
        case 'none':
            preparedData = {}
            preparedFiles = {}
            break
        default:
            break
    }

    const result = {
        obj: {
            headers: preparedHeaders,
            files: preparedFiles,
            data: preparedData,
            method,
            url,
            contentType,
            params: preparedParams
        },
        validation,
        variables

    }

    Logger.log(result, 'RESULT PREPARE FORM TO OBJ')

    return result
}


interface IParsedUrl {
    url: string;
    query: Array<{ key: string; value: string }>;
}

export const parseUrlWithoutSort = (url: string): IParsedUrl => {

    if (!url) {
        return {
            url: '',
            query: []
        }
    }
    try {
        const urlObj = new URL(url);

        const query: Array<{ key: string; value: string }> = [];

        // Используем URLSearchParams.entries() для получения параметров в порядке их следования
        const searchParams = new URLSearchParams(urlObj.search);


        for (const [key, value] of searchParams.entries()) {
            query.push({ key, value });
        }

        // Возвращаем базовый URL без query параметров
        const baseUrl = urlObj.origin + urlObj.pathname;

        return {
            url: baseUrl,
            query
        };
    } catch (e) {
        console.error(e)

        return {
            url: '',
            query: []
        }
    }
}

export function stringifyQueryArray (params: { key: string; value: string }[]): string {
    if (params.length === 0) {
        return '';
    }

    const encodedParams = map(params, ({ key, value }: { key: string, value: string }) => {
        // Кодируем ключ и значение для безопасного использования в URL
        const encodedKey = encodeURIComponent(key);
        const encodedValue = encodeURIComponent(value);

        return `${encodedKey}=${encodedValue}`;
    });

    return `${encodedParams.join('&')}`;
}

export const objToMapParams = (obj: Record<string, unknown> | string): IParamEdit[] => {
    if (isString(obj)) {
        try {
            const tryObjParse = JSON.parse(obj)

            return map(entries(tryObjParse), ([key, value]) => ({
                key: String(key),
                value: Array.isArray(value) ? value.join(',') : String(value)
            }))
        } catch {
            return [
                {
                    key: obj,
                    value: ''
                }
            ]

            console.error('[CURL_PARSE_ERROR]: error when try to parse string DATA to object')
        }

    }

    return map(entries(obj), ([key, value]) => ({
        key: String(key),
        value: Array.isArray(value) ? value.join(',') : String(value)
    }))
}

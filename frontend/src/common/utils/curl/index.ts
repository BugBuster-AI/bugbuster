import { TBodyRawType, TBodyType } from '@Common/types/curl.ts';
import { JSONOutput } from 'curlconverter';
import get from 'lodash/get';
import isObject from 'lodash/isObject';
import isString from 'lodash/isString';
import split from 'lodash/split';
import trim from 'lodash/trim';

export * from './transformCurl.ts'


export enum EContentType {
    URLENCODED = 'application/x-www-form-urlencoded',
    FORM_DATA = 'multipart/form-data',
    APPLICATION_JSON = 'application/json',
    APPLICATION_XML = 'application/xml',
    APPLICATION_JAVASCRIPT = 'application/javascript',
    TEXT_HTML = 'text/html',
    TEXT_PLAIN = 'text/plain',
}

export const RAW_BODY_CONTENT_TYPES = [
    EContentType.APPLICATION_JSON,
    EContentType.APPLICATION_XML,
    EContentType.APPLICATION_JAVASCRIPT,
    EContentType.TEXT_HTML,
    EContentType.TEXT_PLAIN,
]

interface ICurlInfo {
    mode: TBodyType
}

export const getBodyTypeFromContentType = (contentType?: EContentType | null): TBodyRawType => {
    switch (contentType) {
        case EContentType.APPLICATION_JSON:
            return 'json'
        case EContentType.APPLICATION_XML:
            return 'xml'
        case EContentType.APPLICATION_JAVASCRIPT:
            return 'javascript'
        case EContentType.TEXT_HTML:
            return 'html'
        case EContentType.TEXT_PLAIN:
            return 'text'
        default:
            return 'json'
    }
}

export const getContentTypeFromMode = (mode?: TBodyType, rawType?: TBodyRawType): EContentType | null => {
    switch (mode) {
        case 'raw':

            if (rawType) {
                let contentType

                switch (rawType) {
                    case 'json':
                        contentType = EContentType.APPLICATION_JSON
                        break
                    case 'xml':
                        contentType = EContentType.APPLICATION_XML
                        break
                    case 'javascript':
                        contentType = EContentType.APPLICATION_JAVASCRIPT
                        break
                    case 'html':
                        contentType = EContentType.TEXT_HTML
                        break
                    case 'text':
                        contentType = EContentType.TEXT_PLAIN
                        break
                    default:
                        contentType = EContentType.APPLICATION_JSON
                        break
                }

                return contentType
            }

            return EContentType.APPLICATION_JSON
        case 'urlEncoded':
            return EContentType.URLENCODED
        case 'formData':
            return EContentType.FORM_DATA
        case 'none':
            return null
        default:
            return EContentType.APPLICATION_JSON
    }
}

export const getContentType = (headers?: Record<string, unknown>, defaultData = true): string | null => {
    const rawData = (
        get(headers, 'Content-Type', null) ||
        get(headers, 'content-type', null) ||
        get(headers, 'content-Type', null)
    ) as string | null

    const data = split((rawData || ''), ';')[0]

    const contentType = data ? trim(data) : null

    // Если контент тип не указан, по умолчанию ставим form-data
    if (defaultData) {
        return contentType || EContentType.FORM_DATA
    }

    return contentType
}

export const getCurlMode = (contentType?: EContentType | null, data?: any): TBodyType => {
    switch (contentType) {
        case EContentType.APPLICATION_JSON:
        case EContentType.APPLICATION_JAVASCRIPT:
        case EContentType.TEXT_HTML:
        case EContentType.TEXT_PLAIN:
        case EContentType.APPLICATION_XML:
            return 'raw'
        case EContentType.URLENCODED:
            return 'urlEncoded'
        case EContentType.FORM_DATA:
            return 'formData'
        default:
            if (isString(data) || isObject(data)) {
                return 'raw'
            }

            return 'none'
    }
}


export const getCurlInfo = (curl: JSONOutput) => {
    const contentType = get(curl, `headers['Content-Type']`, null)

    return {
        mode: getCurlMode(contentType as EContentType)
    } as ICurlInfo
}


import { IStep } from '@Common/types';
import { EContentType, getContentType, transformCurlToJson, transformCurlToJsonBoundary } from '@Common/utils';
import { generateCurl } from '@Common/utils/generateCurl.ts';
import { Logger } from '@Common/utils/logger/log.ts';
import { CurlValidationError } from '@Entities/test-case/components/Form/components/ApiInput/errors.ts';
import { ICurlConvertedObject, ICurlObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import get from 'lodash/get';
import isString from 'lodash/isString';


export const prepareCurlJson = (data?: ICurlConvertedObject): ICurlObject => {
    Logger.log('prepareCurlJson TRIGGERED', data)
    const headers = get(data, 'headers', {})
    // Если content type не указан, по умолчанию ставим form-data
    const contentType = getContentType(headers, false) as EContentType


    let headersWithContentType = {
        ...headers
    }

    if (data?.method !== 'GET') {
        if (contentType) {
            headersWithContentType['Content-Type'] = contentType
        }
    }

    const resultData = get(data, 'data', {})
    const files = get(data, 'files', {})

    const params = get(data, 'queries', {})
    const method = get(data, 'method', 'GET').toUpperCase()

    const url = get(data, 'location', null) || get(data, 'raw_url', null) || ''

    return { headers: headersWithContentType, data: resultData, files, contentType, url, method, params }
}

export const transformJsonToCurl = async (obj: ICurlObject | string): Promise<string> => {
    if (isString(obj)) {
        return obj
    }
    try {
        const { url, ...rest } = obj || {}

        let objData = {}

        if (!isString(rest?.data)) {
            objData = { ...rest?.data, ...rest?.files }
        } else {
            objData = rest?.data || {}
        }

        // HINT: апдейт для корректного определения курла чтобы избежать оишбки в httpsnippet
        const headers = obj.contentType ? {
            'Content-Type': 'multipart/form-data',
            ...rest.headers
        } : rest.headers

        return await generateCurl({
            url: url || '',
            body: objData ?? {},
            headers: headers as unknown as Record<string, string> ?? {},
            method: rest?.method as 'GET' || 'GET',
        })


    } catch {
        return JSON.stringify(obj)
    }
}

export const formatCurl = (curl: string) => {
    try {
        const rawCurlObj = transformCurlToJson(curl)
        const preparedCurlObj = prepareCurlJson(rawCurlObj)
        // const formattedCurlString = transformJsonToCurl(preparedCurlObj)

        return {
            obj: preparedCurlObj,
            string: curl
        }
    } catch (e) {
        const error = e as CurlValidationError

        console.error(error)
        throw new CurlValidationError(error.message || 'format curl error', curl)
    }
}
export const formatCurlAsync = async (curl: string) => {
    try {
        const rawCurlObj = await transformCurlToJsonBoundary(curl)
        const preparedCurlObj = prepareCurlJson(rawCurlObj)
        // const formattedCurlString = transformJsonToCurl(preparedCurlObj)

        return {
            obj: preparedCurlObj,
            string: curl
        }
    } catch (e) {
        const error = e as CurlValidationError

        console.error(error)
        throw new CurlValidationError(error.message || 'format curl error', curl)
    }
}

export const apiDataToCurlObj = (data: IStep['apiData']): ICurlObject => {

    const contentType = getContentType(data?.headers) as EContentType

    return {
        url: data?.url || '',
        headers: data?.headers || {},
        data: data?.data || {},
        files: data?.files || {},
        method: data?.method || 'GET',
        contentType: contentType,
    }
}

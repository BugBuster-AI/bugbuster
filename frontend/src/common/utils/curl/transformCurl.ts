import { API_METHODS } from '@Common/consts/common.ts';
import {

    isBoundaryFormat, MultipartParser,
} from '@Common/utils/curl/boundary.ts';
import { CurlValidationError } from '@Entities/test-case/components/Form/components/ApiInput/errors.ts';
import { ICurlConvertedObject } from '@Entities/test-case/components/Form/components/ApiInput/models.ts';
import * as curlconverter from 'curlconverter';
import { JSONOutput } from 'curlconverter';
import includes from 'lodash/includes';

export const transformCurlToJson = (curl?: string): JSONOutput => {
    // const clearedCurl = removeSlashes(curl)

    try {
        if (curl?.startsWith('curl ')) {
            const curlObj = curlconverter.toJsonObject(curl) as ICurlConvertedObject

            if (!includes(API_METHODS, curlObj.method.toUpperCase())) {
                throw new CurlValidationError('incorrect http method', curl)
            }

            return curlObj
        } else {
            throw new CurlValidationError('command must starts with "curl"', curl)
        }
    } catch (e: unknown) {
        const error = e as CurlValidationError

        throw new CurlValidationError(error.message || 'invalid curl', curl)
    }
}

export const transformCurlToJsonBoundary = async (curl?: string): Promise<JSONOutput> => {
    // const clearedCurl = removeSlashes(curl)

    try {
        if (curl?.startsWith('curl ')) {
            const curlObj = curlconverter.toJsonObject(curl) as ICurlConvertedObject

            if (!includes(API_METHODS, curlObj.method.toUpperCase())) {
                throw new CurlValidationError('incorrect http method', curl)
            }

            if (curlObj.data && isBoundaryFormat(curlObj.data as string)) {
                try {
                    curlObj.data = await MultipartParser.parse(curlObj.data);
                } catch (parseError) {
                    console.warn('Ошибка парсинга multipart данных:', parseError);
                }
            }

            return curlObj
        } else {
            throw new CurlValidationError('command must starts with "curl"', curl)
        }
    } catch (e: unknown) {
        const error = e as CurlValidationError

        throw new CurlValidationError(error.message || 'invalid curl', curl)
    }
}

export const getCurlObj = (curl?: string): ReturnType<typeof transformCurlToJson> | null => {
    if (!curl) {
        return null
    }
    try {
        return transformCurlToJson(curl)
    } catch (e) {
        console.error(e)

        return null
    }
}

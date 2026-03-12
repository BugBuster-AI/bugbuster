import { ApiError } from '@Common/types';
import { AxiosError } from 'axios';

interface IProps {
    error?: ApiError | Error | null
    needConvertResponse?: boolean
    defaultMessage?: string | null
}

const DEFAULT_ERROR = 'Process error'

export const getErrorMessage = ({ error, needConvertResponse, defaultMessage }: IProps) => {
    if (!error) return undefined

    const defaultErrorMessage = defaultMessage === null ? undefined : defaultMessage || DEFAULT_ERROR

    if (needConvertResponse) {
        const convertedError =
            (((error as unknown as AxiosError)?.response?.data) as ApiError)?.detail

        if (typeof convertedError === 'string') {
            return convertedError
        }

        return defaultErrorMessage
    }

    if (error instanceof Error) {
        return defaultErrorMessage
    }

    const { detail } = error || {}

    if (typeof detail === 'string') {
        return detail
    }

    return defaultErrorMessage
}

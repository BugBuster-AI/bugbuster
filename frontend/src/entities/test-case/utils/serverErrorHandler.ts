import { jsonrepair } from 'jsonrepair';

interface IProps {
    error: any
    onError?: (value: string) => void
}

export const serverErrorHandler = ({ error, onError }: IProps) => {
    const details = error.detail

    if (typeof details === 'string') {
        try {
            const cleanedDetail = jsonrepair(details)

            return JSON.parse(cleanedDetail)
        } catch (e) {

            onError?.(e as string)

            return details
        }
    }

    return details
}

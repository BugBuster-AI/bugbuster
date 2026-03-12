import { COMMON_SEARCH_PARAMS } from '@Common/consts';
import { objectToQueryParams } from '@Common/utils/objToString.ts';
import { decodeParams } from '@Common/utils/transformQueryParams.ts';
import { useSearchParams } from 'react-router-dom';

interface IProps {
    rules?: () => string | number
    additionalParams?: Record<string, string>
    root?: string
}

// Хук для получения обратного пути при редиректе
export const useBackPath = () => {
    const [searchParams] = useSearchParams()
    const backUrl = searchParams.get(COMMON_SEARCH_PARAMS.BACK_URL)
    const backState = searchParams.get(COMMON_SEARCH_PARAMS.BACK_STATE)

    const getBackPath = ({ rules, root, additionalParams }: IProps) => {
        let params = ''

        if (additionalParams) {
            params = `&${objectToQueryParams(additionalParams)}`
        }

        if (backUrl) {
            return `${decodeParams(backUrl)}${params}`
        }

        if (backState) {
            return `${root || ''}?${decodeParams(backState)}${params}`
        }

        if (rules) {
            return rules()
        }

        return root
    }

    return {
        getBackPath
    }
}

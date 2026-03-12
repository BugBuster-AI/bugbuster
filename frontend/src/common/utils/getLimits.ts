import isNil from 'lodash/isNil';

interface IProps {
    limitValue?: number;
    remaining?: number
}

interface IReturn {
    available: boolean
    title: string
}

export const getLimits = ({ limitValue, remaining }: IProps): IReturn => {

    if (isNil(limitValue) || isNil(remaining)) {
        return {
            title: '',
            available: false
        }
    }

    const title = limitValue >= 0 ? `${remaining}/${limitValue}` : 'Unlimited'

    return {
        available: remaining > 0,
        title
    }
}

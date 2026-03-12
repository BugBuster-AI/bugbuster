import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';

export const parseToString = (data: Record<string, string>): string => {
    if (isEmpty(data)) return ''

    return map(data, (value, key) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`).join('&');
}

export * from './token.ts'
export * from './async.ts'
export * from './getTransformedSteps'
export * from './getStatusColors'
export * from './groupSteps'
export * from './curl'

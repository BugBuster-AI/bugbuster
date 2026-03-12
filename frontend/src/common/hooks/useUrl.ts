import qs from 'query-string';

export const useUrl = (val: string) => {
    return qs.parseUrl(val)
}

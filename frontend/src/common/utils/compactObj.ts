import omitBy from 'lodash/omitBy';

export const compactObj = <T extends string, U extends unknown, >(obj: Record<T, U>): Record<T, NonNullable<U>> => {
    return omitBy(obj, (value) => !value) as Record<T, NonNullable<U>>
}

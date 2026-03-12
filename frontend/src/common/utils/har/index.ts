import entries from 'lodash/entries';
import isString from 'lodash/isString';
import map from 'lodash/map';

export const objectToHar = (obj?: Record<string, string> | string): { name: string, value: string }[] => {
    if (!obj) {
        return []
    }
    if (isString(obj)) {
        return [
            {
                name: obj as string,
                value: ''
            }
        ]
    }

    return map(entries(obj), ([name, value]) => ({ name, value }))
}

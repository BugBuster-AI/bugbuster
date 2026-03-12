import entries from 'lodash/entries';
import forEach from 'lodash/forEach';

export const objectToQueryParams = (obj: Record<string, string | number>) => {
    const params = new URLSearchParams();

    forEach(entries(obj), ([key, value]) => {
        if (value == null || value === '') return;

        if (Array.isArray(value)) {
            value.forEach((item) => params.append(key, item));
        } else {
            params.append(key, String(value));
        }
    });

    return params.toString();
}

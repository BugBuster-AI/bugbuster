type DeepPartial<T> = {
    [P in keyof T]?:  T[P] extends object
        ? T[P] extends any[]
            ? T[P]
            : DeepPartial<T[P]>
        : T[P]
}

export const deepMerge = <T extends Record<string, any>>(
    target: T,
    source: DeepPartial<T>
): T => {
    const result = { ...target }

    for (const key in source) {
        if (! source.hasOwnProperty(key)) {
            continue
        }

        const sourceValue = source[key]
        const targetValue = result[key]

        if (
            sourceValue &&
            typeof sourceValue === 'object' &&
            ! Array.isArray(sourceValue) &&
            targetValue &&
            typeof targetValue === 'object' &&
            !Array. isArray(targetValue)
        ) {
            result[key] = deepMerge(targetValue, sourceValue)
        }
        else {
            result[key] = sourceValue as T[typeof key]
        }
    }

    return result
}

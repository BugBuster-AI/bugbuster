import isString from 'lodash/isString';

interface BaseStep {
    // Могут быть общие поля, например, id: string | number;
}

/**
 * Описывает объект-правило, где ключ - это индекс, а значение - вставляемый объект.
 */
interface IndexRuleObject<U> {
    [index: string | number]: U;
}

/**
 * Описывает массив "слоев", каждый из которых содержит массив правил.
 */
type IndexLayers<U> = Array<Array<IndexRuleObject<U>>>;

/**
 * Параметры для функции insertIndexesInArray.
 */
interface Props<T> {
    items: T[];
    indexLayers: IndexLayers<T>;
    transformIndexItem?: (item: T & { originalValue: T | undefined }) => T;
    transform?: (item: T) => T
}

/**
 * Вставляет элементы из многоуровневой структуры `indexLayers` в массив `items`.
 *
 * @param props - Объект с исходным массивом, слоями для вставки и функцией-трансформером.
 * @returns Новый массив, где каждый элемент дополнен свойством `localIndex`.
 */
export function insertIndexesInArray<T extends BaseStep> (
    {
        items,
        indexLayers,
        transformIndexItem,
        transform
    }: Props<T>
): (T & { localIndex: number })[] {
    // Создаем рабочую копию, чтобы не изменять исходный массив.
    let result: T[] = [...items];

    // 1. Собираем все правила вставки из всех слоев в один плоский массив.
    const allInsertions: {
        index: number; // Целевой индекс вставки в *оригинальном* массиве
        value: T,
        layerIndex: number, // Индекс слоя для сохранения приоритета
        originalOrder: number, // Порядок внутри слоя
    }[] = [];

    indexLayers.forEach((layer, layerIndex) => {
        let orderCounter = 0;

        for (const ruleObject of layer) {
            for (const key in ruleObject) {
                if (Object.prototype.hasOwnProperty.call(ruleObject, key)) {
                    const index = parseInt(key, 10);

                    if (!isNaN(index)) {
                        allInsertions.push({
                            index,
                            value: ruleObject[key],
                            layerIndex,
                            originalOrder: orderCounter++,
                        });
                    }
                }
            }
        }
    });

    /*
     * 2. Сортируем все вставки.
     * - Сначала по индексу вставки в ОБРАТНОМ порядке (чтобы не смещать последующие индексы).
     * - Затем по индексу слоя (для приоритета).
     * - Затем по оригинальному порядку внутри слоя.
     */
    allInsertions.sort((a, b) => {
        if (a.index !== b.index) {
            return b.index - a.index;
        }
        if (a.layerIndex !== b.layerIndex) {
            return b.layerIndex - a.layerIndex;
        }

        return b.originalOrder - a.originalOrder;
    });

    // 3. Вставляем элементы в результирующий массив за один проход.
    for (const insertion of allInsertions) {
        const { index, value } = insertion;

        // Получаем оригинальный элемент, *если* он существует по этому индексу
        const originalValue = (index >= 0 && index < items.length) ? items[index] : items[0];

        let resultValue: T;

        const rawValue = {
            ...value,
            originalIndex: index,
            originalValue
        };

        if (transformIndexItem) {
            // @ts-ignore
            resultValue = transformIndexItem(rawValue);
        } else {
            resultValue = rawValue as unknown as T;
        }

        if (index === -1) {
            result.unshift(resultValue); // Вставка в начало
        } else if (index >= 0 && index < items.length) {
            // Вставляем ПОСЛЕ указанного индекса оригинального массива
            result.splice(index + 1, 0, resultValue);
        } else if (index >= items.length) {
            // Если индекс больше или равен длине, вставляем в конец
            result.push(resultValue);
        } else {
            console.error(
                `Ошибка: Неверный индекс ${index}. ` +
                `Допустимые значения: -1 (для вставки в начало) или от 0 до ${items.length}.`
            );
        }
    }


    console.log(result, 'RESULT')

    // @ts-ignore
    return result.map((element, index) => {
        const transformedElement = transform ? transform(element) : element;

        if (isString(element)) {
            return {
                value: transformedElement,
                localIndex: index
            };
        }

        return {
            ...transformedElement,
            localIndex: index,
        };
    });
}

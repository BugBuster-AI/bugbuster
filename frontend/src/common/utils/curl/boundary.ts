import { parse } from 'parse-multipart-data';

// Проверяет, содержит ли строка типичный паттерн boundary
export function isBoundaryFormat (str: any) {
    if (!str || typeof str !== 'string') {
        return false;
    }

    return /^----\w+/.test(str) ||
        /boundary=/i.test(str) ||
        /^--[a-zA-Z0-9]+/.test(str) ||
        str.includes('Content-Disposition: form-data');
}


export class MultipartParser {
    /**
     * Проверяет, является ли строка данными в формате multipart с boundary.
     * @param {string} data - Входная строка.
     * @returns {boolean} - True, если это boundary-формат.
     */
    static isBoundaryFormat (data) {
        // Проверяем наличие boundary-паттерна: начинается с -- и содержит буквенно-цифровые символы
        const boundaryPattern = /^--[a-zA-Z0-9'()+_,-./:=?]{1,70}(\r\n|\n)/;

        return boundaryPattern.test(data);
    }

    /**
     * Извлекает boundary из сырых данных.
     * @param {string} rawData - Входная строка.
     * @returns {string} - Boundary без ведущих '--'.
     */
    static extractBoundary (rawData) {
        const firstLine = rawData.split('\n')[0].trim();

        if (!firstLine.startsWith('--')) {
            throw new Error('Invalid boundary format: must start with --');
        }

        return firstLine.substring(2); // Убираем ведущие '--'
    }

    /**
     * Парсит raw-строку с boundary в объект.
     * @param {string} rawData - Входная строка.
     * @returns {Object} - Распарсенные данные.
     */
    static parseBoundaryData (rawData) {
        const boundary = this.extractBoundary(rawData);
        // Конвертируем строку в ArrayBuffer для библиотеки parse-multipart-data
        const encoder = new TextEncoder();
        const buffer = encoder.encode(rawData);
        //@ts-ignore
        const parts = parse(buffer, boundary);

        const result = {};

        parts.forEach((part) => {
            const name = part.name;

            if (!name) return

            // Если часть является файлом, сохраняем объект с данными и именем файла
            if (part.filename) {
                result[name] = {
                    filename: part.filename,
                    data: part.data, // Это Uint8Array
                    type: part.type
                };
            } else {
                // Для текстовых полей преобразуем Uint8Array в строку
                const decoder = new TextDecoder();

                result[name] = decoder.decode(part.data);
            }
        });

        return result;
    }

    /**
     * Основной метод: парсит строку или возвращает её значение.
     * @param {string} data - Входная строка.
     * @returns {Object|string} - Объект с данными или исходная строка.
     */
    static parse (data) {
        if (this.isBoundaryFormat(data)) {
            return this.parseBoundaryData(data);
        } else {
            return data; // Возвращаем как есть, если не boundary
        }
    }
}

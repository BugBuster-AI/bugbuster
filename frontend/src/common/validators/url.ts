import { Rule } from 'antd/es/form';

/**
 * Проверяет наличие точки в URL (для доменной зоны)
 * @param errorMessage - сообщение об ошибке
 */
export const urlValidator = (errorMessage: string): Rule => ({
    validator: (_, value) => {
        if (!value) {
            return Promise.resolve();
        }

        if (typeof value !== 'string') {
            return Promise.reject(new Error(errorMessage));
        }

        if (!value.startsWith('http://') && !value.startsWith('https://') && !value.startsWith('www.') ) {
            return Promise.reject(new Error(errorMessage));
        }

        /* Проверяем наличие точки в URL (означает наличие доменной зоны) */
        if (!value.includes('.')) {
            return Promise.reject(new Error(errorMessage));
        }

        return Promise.resolve();
    }
});

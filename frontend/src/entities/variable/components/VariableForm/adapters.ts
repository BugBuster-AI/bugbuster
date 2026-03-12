import { IVariable } from '@Entities/variable/models';
import { SPECIAL_FORMATS } from './consts';

// Маппинг сокращений единиц времени на полные названия
const UNIT_SHORT_TO_FULL: Record<string, string> = {
    's': 'seconds',
    'm': 'minutes',
    'h': 'hours',
    'd': 'days',
    'M': 'months',
    'y': 'years'
};

const UNIT_FULL_TO_SHORT: Record<string, string> = {
    'seconds': 's',
    'minutes': 'm',
    'hours': 'h',
    'days': 'd',
    'months': 'M',
    'years': 'y'
};

export interface IVariableFormData {
    variable_name: string;
    variable_description?: string | null;
    variable_config: {
        type: 'simple' | 'time';
        value?: string;
        base?: string;
        utc_offset?: string;
        shifts?: Array<{
            value: number | string;
            type: string;
        }>;
        format?: string;
        'is-const'?: boolean;
    };
    customFormat?: string;
    variable_details_id?: string;
    variables_kit_id?: string;
}

/**
 * Преобразует HTTP данные (IVariable) в данные формы
 */
export const toFormData = (httpData: IVariable): IVariableFormData => {
    const formData: IVariableFormData = {
        variable_name: httpData.variable_name || '',
        variable_description: httpData.variable_description,
        variable_config: {
            type: httpData.variable_config.type || 'simple',
        },
        variable_details_id: httpData.variable_details_id,
        variables_kit_id: httpData.variables_kit_id,
    };

    if (httpData.variable_config.type === 'simple') {
        formData.variable_config.value = httpData.variable_config.value || '';
    }

    if (httpData.variable_config.type === 'time') {
        formData.variable_config.base = httpData.variable_config.base;
        formData.variable_config.utc_offset = httpData.variable_config.utc_offset;
        formData.variable_config['is-const'] = httpData.variable_config.is_const;

        // Преобразуем shifts из формата HTTP (unit: "d") в формат формы (type: "days")
        if (httpData.variable_config.shifts) {
            formData.variable_config.shifts = httpData.variable_config.shifts.map((shift) => ({
                value: shift.value,
                type: UNIT_SHORT_TO_FULL[shift.unit] || shift.unit
            }));
        }

        // Обрабатываем формат - если это кастомный формат, разделяем на format и customFormat
        const httpFormat = httpData.variable_config.format;
        const standardFormats = [
            'YYYY-MM-DD',
            'DD.MM.YYYY',
            'MM/DD/YYYY',
            'YYYY-MM-DD HH:mm:ss',
            'YYYY-MM-DD HH:mm',
            'HH:mm:ss',
            'HH:mm',
            'X',
            'x'
        ];

        if (httpFormat) {
            if (standardFormats.includes(httpFormat)) {
                formData.variable_config.format = httpFormat;
            } else {
                // Если формат не стандартный - это кастомный формат
                formData.variable_config.format = SPECIAL_FORMATS.CUSTOM_FORMAT;
                formData.customFormat = httpFormat;
            }
        }
    }

    return formData;
};

/**
 * Преобразует данные формы в HTTP данные для отправки на сервер
 */
export const toHttpData = (formData: IVariableFormData): Partial<IVariable> => {
    const httpData: Partial<IVariable> = {
        variable_name: formData.variable_name,
        variable_description: formData.variable_description || null,
        variable_config: {
            type: formData.variable_config.type,
            value: null,
        },
    };

    if (formData.variable_details_id) {
        httpData.variable_details_id = formData.variable_details_id;
    }

    if (formData.variables_kit_id) {
        httpData.variables_kit_id = formData.variables_kit_id;
    }

    if (formData.variable_config.type === 'simple') {
        httpData.variable_config!.value = formData.variable_config.value || null;
    }

    if (formData.variable_config.type === 'time') {
        httpData.variable_config!.base = formData.variable_config.base;
        httpData.variable_config!.utc_offset = formData.variable_config.utc_offset || undefined;
        httpData.variable_config!.format = formData.variable_config.format || undefined;
        httpData.variable_config!.is_const = formData.variable_config['is-const'];

        // Преобразуем shifts из формата формы (type: "days") в формат HTTP (unit: "d")
        if (formData.variable_config.shifts) {
            httpData.variable_config!.shifts = formData.variable_config.shifts.map((shift) => ({
                value: Number(shift.value),
                unit: UNIT_FULL_TO_SHORT[shift.type] || shift.type
            }));
        }

        
        if (formData.variable_config.format) {
            if (formData.variable_config.format === SPECIAL_FORMATS.CUSTOM_FORMAT && formData.customFormat) {
                 httpData.variable_config!.format = formData.customFormat;
            } else {
                 httpData.variable_config!.format = formData.variable_config.format;
            }
        } else {
             // Если формат не указан, явно устанавливаем null
             httpData.variable_config!.format = null;
        }
         
    }

    return httpData;
};

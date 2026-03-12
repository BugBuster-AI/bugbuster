import { TranslationType } from '@Common/types'

export const VariableTypes = {
    CONSTANT: 'constant',
    TIME: 'time'
} as const

export const SPECIAL_FORMATS = {
    CUSTOM_FORMAT: 'custom_format'
}

export const BASE_VARIABLES_LIST = (t: TranslationType) => ({
    currentDate: t('baseList.currentDate'),
    currentTime: t('baseList.currentTime'),
    dateTime: t('baseList.dateTime'),
    timestamp: t('baseList.timestamp'),
    today: t('baseList.today'),
    yesterday: t('baseList.yesterday'),
    tomorrow: t('baseList.tomorrow'),
    startOfDay: t('baseList.startOfDay'),
    endOfDay: t('baseList.endOfDay'),
})

export const TIMEZONE_LIST = () => ({
    '-12:00': 'UTC -12:00 (Baker Island)',
    '-11:00': 'UTC -11:00 (American Samoa)',
    '-10:00': 'UTC -10:00 (Hawaii)',
    '-09:00': 'UTC -09:00 (Alaska)',
    '-08:00': 'UTC -08:00 (Los Angeles)',
    '-07:00': 'UTC -07:00 (Denver)',
    '-06:00': 'UTC -06:00 (Chicago)',
    '-05:00': 'UTC -05:00 (New York)',
    '-04:00': 'UTC -04:00 (Halifax)',
    '-03:00': 'UTC -03:00 (São Paulo)',
    '-02:00': 'UTC -02:00 (South Georgia)',
    '-01:00': 'UTC -01:00 (Azores)',
    '+00:00': 'UTC +00:00 (London)',
    '+01:00': 'UTC +01:00 (Berlin)',
    '+02:00': 'UTC +02:00 (Athens)',
    '+03:00': 'UTC +03:00 (Moscow)',
    '+04:00': 'UTC +04:00 (Dubai)',
    '+05:00': 'UTC +05:00 (Karachi)',
    '+05:30': 'UTC +05:30 (Mumbai)',
    '+06:00': 'UTC +06:00 (Dhaka)',
    '+07:00': 'UTC +07:00 (Bangkok)',
    '+08:00': 'UTC +08:00 (Singapore)',
    '+09:00': 'UTC +09:00 (Tokyo)',
    '+10:00': 'UTC +10:00 (Sydney)',
    '+11:00': 'UTC +11:00 (Solomon Islands)',
    '+12:00': 'UTC +12:00 (Auckland)',
    '+13:00': 'UTC +13:00 (Tonga)',
    '+14:00': 'UTC +14:00 (Kiribati)',
})

export const FORMAT_LIST = () => ({
    'YYYY-MM-DD': 'YYYY-MM-DD (2025-11-03)',
    'DD.MM.YYYY': 'DD.MM.YYYY (03.11.2025)',
    'MM/DD/YYYY': 'MM/DD/YYYY (11/03/2025)',
    'YYYY-MM-DD HH:mm:ss': 'YYYY-MM-DD HH:mm:ss (2025-11-03 14:30:00)',
    'YYYY-MM-DD HH:mm': 'YYYY-MM-DD HH:mm (2025-11-03 14:30)',
    'HH:mm:ss': 'HH:mm:ss (14:30:00)',
    'HH:mm': 'HH:mm (14:30)',
    'X': 'X (1730545800)',
    'x': 'x (1730545800000)',
    [SPECIAL_FORMATS.CUSTOM_FORMAT]: 'Custom format'  
})

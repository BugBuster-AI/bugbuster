export const VERSION = import.meta.env.VITE_APP_VERSION || 'ru' as 'ru' | 'ai'
/** UI and flows that send language to the API: English only (no Russian locale in the app). */
export const LANGUAGE = 'en' as const

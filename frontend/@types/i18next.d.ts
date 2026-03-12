// i18next.d.ts
import 'i18next';
import enTranslations from '../src/locales/en/translation.json';

// Определите тип для ваших переводов
type Translations = typeof enTranslations;

// Расширьте типы i18next
declare module 'i18next' {
  interface CustomTypeOptions {
    resources: {
      translation: Translations;
    };
  }
}
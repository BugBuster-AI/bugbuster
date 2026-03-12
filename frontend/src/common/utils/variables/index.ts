export function replaceTemplateVariables (template: string, values: Record<string, string>): string {
    // Регулярное выражение для поиска всех вхождений {{key}}
    // /g флаг обеспечивает замену всех найденных совпадений, а не только первого.
    // \s* позволяет игнорировать пробелы внутри скобок, например {{ name }}.
    // (\w+) захватывает имя переменной (буквы, цифры и знак подчеркивания).
    const regex = /{{\s*(\w+)\s*}}/g;

    // Используем функцию обратного вызова в методе replace
    return template.replace(regex, (match, key) => {
        /*
         * match - это полное совпадение (например, "{{name}}")
         * key - это захваченная группа (имя переменной, например, "name")
         */

        /*
         * Проверяем, существует ли ключ в объекте values
         * Используем Object.prototype.hasOwnProperty.call для безопасной проверки
         */
        if (Object.prototype.hasOwnProperty.call(values, key)) {
            return values[key];
        }

        // Если ключ не найден в объекте, оставляем переменную как есть
        return match;
    });
}

import { IExtraCaseType, ITestCaseVariable } from '@Entities/test-case/models/test-case-variables.ts';

interface IProps {
    value: string
    extra?: IExtraCaseType
}

function escapeHtml (unsafe: string): string {
    return unsafe
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

export const parseVariablesInStep = (step: IProps, key: string = 'value'): string => {
    if (!step?.extra?.variables || step?.extra?.variables?.length === 0) {

        return step.value;
    }

    let result = step.value;
    const replacements: { start: number; end: number; variable: ITestCaseVariable }[] = [];

    // Собираем все замены с исходными позициями
    step.extra.variables.forEach((variable) => {
        variable.positions.forEach((pos) => {
            const start = pos[0];
            const end = pos[1];

            if (variable.key !== key) {
                return
            }

            // Проверяем, что позиции валидны
            if (
                typeof start === 'number' &&
                typeof end === 'number' &&
                start >= 0 &&
                end <= step.value.length &&
                start <= end
            ) {
                replacements.push({
                    start,
                    end,
                    variable
                });
            }
        });
    });

    // Сортируем замены по убыванию позиции начала (для замены с конца)
    replacements.sort((a, b) => b.start - a.start);

    // Выполняем замены с конца строки
    for (const replacement of replacements) {
        const startIdx = replacement.start;
        const endIdx = replacement.end; // Убрали +1, так как end уже указывает на последний символ

        const before = result.substring(0, startIdx);
        const after = result.substring(endIdx);

        const escapedValue = escapeHtml(replacement.variable.value);

        result = `${before}{{${escapedValue}}}${after}`;
    }

    return result;
}

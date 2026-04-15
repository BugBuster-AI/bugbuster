import { ansiToReactNodes } from '@Features/test-case/playwright-codegen/codegenLogAnsi';
import { type CSSProperties, type ReactNode } from 'react';

interface TProps {
    text: string | null | undefined;
    style?: CSSProperties;
    className?: string;
}

/**
 * Текст ошибок из Playwright/Node часто содержит ANSI (dim и т.д.).
 * Рендерим с «подсветкой» через anser; без ESC-кодов ведёт себя как обычный текст.
 */
export const RunErrorText = ({ text, style, className }: TProps): ReactNode => {
    if (text == null || text === '') {
        return null;
    }

    return (
        <span className={ className } style={ { whiteSpace: 'pre-line', ...style } }>
            {ansiToReactNodes(text)}
        </span>
    );
};

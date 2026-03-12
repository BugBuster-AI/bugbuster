import parse from 'html-react-parser';
import isString from 'lodash/isString';
import { ReactNode } from 'react';

export const replaceWithReactNode = (text: string, renderFunction: (variable: string, index: number) => ReactNode) => {
    try {

        const parts = text.split(/(\{\{.*?\}\})/);

        return parts.map((part: string, index: number) => {
            const match = part.match(/^\{\{(.*?)\}\}$/);

            if (match) {
                return renderFunction(match[1].trim(), index);
            }

            return part;
        });
    } catch (e) {
        return renderFunction(text, 0)
        console.error(`[REPLACE VARIABLE ERROR]:`, e)
    }
}

export const formatVariableToHTML = (variable: string) => {
    return `<code class="ant-typography" data-variable="${variable}" style="color: #1677ff">${variable}</code>`
}

export const formatVariableToComponent = (variable: any, name?: string | number, addBrases: boolean = false) => {

    const parseVariable = (varStr: any) => {
        if (addBrases) {
            return <>{'{{'}{varStr}{`}}`}</>
        }

        return varStr
    }

    return (
        <code
            key={ name || variable }
            className="ant-typography"
            data-variable={ name || undefined }
            style={ {
                whiteSpace: 'normal',
                color: 'rgba(21, 93, 252, 1)',
                background: 'rgba(3, 7, 18, 0.06)',
                border: `1px solid rgba(217, 217, 217, 1)`,
                fontSize: 12,
                letterSpacing: 0,
                borderRadius: 4,
                lineHeight: '16px',
                padding: '2px 4px',
            } }
        >
            {parseVariable(isString(variable) ? parse(variable) : variable)}
        </code>
    )
}

export const renderStringWithVariables = (text: string, addBraces: boolean = false) => {
    return replaceWithReactNode(
        text,
        (variable, index) => formatVariableToComponent(variable, `var-${index}`, addBraces)
    );
}

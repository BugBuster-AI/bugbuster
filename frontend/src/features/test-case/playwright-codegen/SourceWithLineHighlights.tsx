import { ReactElement, useEffect } from 'react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { github } from 'react-syntax-highlighter/dist/esm/styles/hljs';

export function SourceWithLineHighlights (props: {
    source: string
    highlightFrom: number | null
    highlightTo: number | null
    /** Заполнить доступную высоту во встроенной панели (flex); прокрутка внутри области */
    fillAvailableHeight?: boolean
}): ReactElement {
    const { source, highlightFrom, highlightTo, fillAvailableHeight = false } = props

    useEffect(() => {
        if (highlightFrom == null) return
        const id = `playwright-codegen-line-${highlightFrom}`
        const raf = requestAnimationFrame(() => {
            document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
        })

        return () => cancelAnimationFrame(raf)
    }, [highlightFrom, highlightTo, source])

    const highlighter = (
        <SyntaxHighlighter
            customStyle={ {
                margin: 0,
                ...(fillAvailableHeight ? {} : { maxHeight: 360 }),
                fontSize: 12,
            } }
            language="javascript"
            lineNumberStyle={ {
                minWidth: '2.75em',
                paddingRight: '0.85em',
                userSelect: 'none',
                color: '#8c8c8c',
                borderRight: '1px solid rgba(0, 0, 0, 0.06)',
            } }
            lineProps={ (lineNumber) => {
                const inRange = Boolean(
                    highlightFrom != null && highlightTo != null
                    && lineNumber >= highlightFrom && lineNumber <= highlightTo,
                )

                return {
                    id: lineNumber === highlightFrom ? `playwright-codegen-line-${lineNumber}` : undefined,
                    style: {
                        display: 'block',
                        backgroundColor: inRange
                            ? 'var(--ant-color-primary-bg, rgba(230, 244, 255, 0.92))'
                            : undefined,
                        boxShadow: inRange
                            ? 'inset 3px 0 0 var(--ant-color-primary, #1677ff)'
                            : undefined,
                    },
                }
            } }
            style={ github }
            showLineNumbers
            wrapLines
            wrapLongLines
        >
            {source}
        </SyntaxHighlighter>
    )

    return (
        <div
            style={ fillAvailableHeight
                ? {
                    border: '1px solid var(--ant-color-border-secondary, #f0f0f0)',
                    borderRadius: 8,
                    display: 'flex',
                    flex: 1,
                    flexDirection: 'column',
                    minHeight: 0,
                    overflow: 'hidden',
                }
                : {
                    border: '1px solid var(--ant-color-border-secondary, #f0f0f0)',
                    borderRadius: 8,
                    overflow: 'hidden',
                } }
        >
            {fillAvailableHeight
                ? (
                    <div style={ { flex: 1, minHeight: 0, overflow: 'auto' } }>
                        {highlighter}
                    </div>
                )
                : highlighter}
        </div>
    )
}

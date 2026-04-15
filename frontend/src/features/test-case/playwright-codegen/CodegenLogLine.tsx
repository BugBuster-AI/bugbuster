import { type ICodegenLogEntry } from '@Entities/test-case/models'
import { Tag } from 'antd'
import { type CSSProperties, type ReactElement, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import SyntaxHighlighter from 'react-syntax-highlighter'
import { github } from 'react-syntax-highlighter/dist/esm/styles/hljs'

import { ansiToReactNodes, stripAnsi } from './codegenLogAnsi'

const LEVEL_STYLE: Record<string, CSSProperties> = {
    error: { color: '#cf1322' },
    warn: { color: '#d48806' },
    info: { color: '#8c8c8c' },
}

const PHASE_TAG_COLOR: Record<string, string> = {
    start: 'blue',
    api: 'cyan',
    expected_result: 'cyan',
    llm_draft: 'purple',
    llm_repair: 'purple',
    er_llm_draft: 'purple',
    er_llm_repair: 'purple',
    generated_js: 'geekblue',
    api_validate: 'orange',
    validate: 'orange',
    mcp_run: 'blue',
    er_mcp_run: 'blue',
    nl_validate: 'orange',
    er_validate: 'orange',
    validate_ok: 'green',
    validate_fail: 'red',
    finalize: 'green',
}

function JsCodeBlock ({ code }: { code: string }): ReactElement {
    return (
        <div style={ { marginTop: 4, borderRadius: 6, overflow: 'hidden', border: '1px solid rgba(0,0,0,0.06)' } }>
            <SyntaxHighlighter
                customStyle={ { margin: 0, fontSize: 11, padding: 8 } }
                language="javascript"
                style={ github }
                wrapLongLines
            >
                {code}
            </SyntaxHighlighter>
        </div>
    )
}

interface Props {
    row: ICodegenLogEntry
}

export function CodegenLogLine ({ row }: Props): ReactElement {
    const { t } = useTranslation()
    const level = row.level || 'info'
    const phase = row.phase ?? null
    const stepUid = row.step_uid ? row.step_uid.slice(0, 8) : null
    const rawMessage = row.message ?? ''

    const failshotSrc = useMemo(() => {
        const url = row.screenshot_url?.trim()
        if (url) {
            try {
                const parsed = new URL(url)
                if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return url
            } catch { /* invalid URL — skip */ }
            return null
        }
        const b64 = row.screenshot_base64?.trim()
        if (!b64) return null
        const mime = (row.screenshot_mime_type?.trim() || 'image/jpeg')
        if (mime !== 'image/jpeg' && mime !== 'image/png') return null
        return `data:${mime};base64,${b64}`
    }, [row.screenshot_url, row.screenshot_base64, row.screenshot_mime_type])

    const isGeneratedJs = phase === 'generated_js'
    let headerText: string
    let jsBody: string | null = null

    if (isGeneratedJs) {
        const nlIdx = rawMessage.indexOf('\n')
        if (nlIdx !== -1) {
            headerText = rawMessage.slice(0, nlIdx)
            jsBody = stripAnsi(rawMessage.slice(nlIdx + 1))
        } else {
            headerText = rawMessage
        }
    } else {
        headerText = rawMessage
    }

    return (
        <div style={ { padding: '2px 0' } }>
            <span style={ { ...LEVEL_STYLE[level], fontWeight: 500 } }>
                [{level}]
            </span>
            {phase && (
                <>
                    {' '}
                    <Tag
                        color={ PHASE_TAG_COLOR[phase] ?? 'default' }
                        style={ { fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0, verticalAlign: 'text-bottom' } }
                    >
                        {phase}
                    </Tag>
                </>
            )}
            {stepUid && (
                <span style={ { color: '#8c8c8c', fontFamily: 'monospace', fontSize: 11 } }>
                    {' '}{stepUid}…
                </span>
            )}
            {' '}
            <span>{ansiToReactNodes(headerText)}</span>
            {jsBody && <JsCodeBlock code={ jsBody }/>}
            {failshotSrc && (
                <div style={ { marginTop: 8 } }>
                    <div style={ { fontSize: 11, color: '#8c8c8c', marginBottom: 4 } }>
                        {t('codegen.validation_fail_screenshot_caption')}
                    </div>
                    <img
                        alt=""
                        src={ failshotSrc }
                        style={ {
                            maxWidth: '100%',
                            maxHeight: 420,
                            objectFit: 'contain',
                            borderRadius: 6,
                            border: '1px solid rgba(0,0,0,0.08)',
                            display: 'block',
                        } }
                    />
                </div>
            )}
        </div>
    )
}

import type { ICodegenStepSpan } from '@Entities/test-case/models'

/**
 * Вырезает строки source_code по span для step_uid (линии 1-indexed, как в артефакте codegen).
 */
export function extractCodegenSnippetForStep (
    sourceCode: string,
    stepSpans: ICodegenStepSpan[],
    stepUid: string | null,
): string | null {
    if (!stepUid) {
        return null
    }
    const span = stepSpans.find((s) => s.step_uid === stepUid)
    if (!span) {
        return null
    }
    const start = Math.max(1, span.start_line)
    const end = Math.max(start, span.end_line)
    const normalized = sourceCode.replace(/\r\n/g, '\n')
    const lines = normalized.split('\n')
    if (start > lines.length) {
        return null
    }
    const slice = lines.slice(start - 1, end)
    const text = slice.join('\n').trimEnd()

    return text.length > 0 ? text : null
}

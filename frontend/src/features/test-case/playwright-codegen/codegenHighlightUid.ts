import { IRunStep } from '@Entities/runs/models';
import { ITestCase, ITestCaseStep } from '@Entities/test-case/models';

/**
 * IMPORTANT: must match AUTORUN_SECTIONS in clicker/src/codegen/case_steps.py
 * and normalized_nl_vectors in backend/api/services/steps_nl_normalization.py.
 * Changing order here will break step_uid ↔ step_spans mapping.
 */
const CASE_SECTION_KEYS: (keyof ITestCase)[] = [
    'before_browser_start',
    'before_steps',
    'steps',
    'after_steps',
];

function flattenCaseStepUids (testCase: ITestCase): string[] {
    const out: string[] = []
    let runIdx = 0
    for (const key of CASE_SECTION_KEYS) {
        const arr = (testCase[key] as ITestCaseStep[] | undefined) ?? []
        for (const s of arr) {
            out.push(s.step_uid ?? `idx_${runIdx}`)
            runIdx++
        }
    }
    return out
}

/** step_uid для подсветки фрагмента в артефакте по шагу прогона. */
export function codegenHighlightUidFromRunStep (
    step: Partial<IRunStep> | null | undefined,
    testCase: ITestCase | undefined,
): string | null {
    if (!step || !testCase) return null

    if ((step as Record<string, unknown>).step_uid) {
        return (step as Record<string, unknown>).step_uid as string
    }

    const idx = step.index_step
    if (typeof idx !== 'number' || idx < 0) return null
    const uids = flattenCaseStepUids(testCase)
    return uids[idx] ?? null
}

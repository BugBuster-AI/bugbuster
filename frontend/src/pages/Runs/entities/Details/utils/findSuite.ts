import { ISuiteInGroupedRun } from '@Entities/runs/models';
import find from 'lodash/find';
import size from 'lodash/size';

export const findSuiteByCaseId = (suites?: ISuiteInGroupedRun[], caseId?: string) => {
    if (!suites || !caseId) return null
    let resultSuite: ISuiteInGroupedRun | null = null

    for (const suite of suites) {
        if (find(suite.cases, { group_run_case_id: caseId })) {
            resultSuite = suite
        } else if (size(suite.children)) {
            findSuiteByCaseId(suite.children, caseId)
        }
    }

    return resultSuite
}

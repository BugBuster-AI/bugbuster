import { ISuiteInGroupedRun, ITestCaseInGroupedRun } from '@Entities/runs/models';
import find from 'lodash/find';
import reduce from 'lodash/reduce';

export const findCaseById = (suites?: ISuiteInGroupedRun[], caseId?: string): ITestCaseInGroupedRun | undefined => {
    if (!suites || !caseId) return undefined

    return reduce(suites, (result, suite) => {
        const caseInCurrentSuite = find(suite.cases, { group_run_case_id: caseId });

        if (caseInCurrentSuite) return caseInCurrentSuite;

        const caseInChildren = findCaseById(suite.children, caseId);

        if (caseInChildren) return caseInChildren;

        return result;
    }, undefined as ITestCaseInGroupedRun | undefined);
}

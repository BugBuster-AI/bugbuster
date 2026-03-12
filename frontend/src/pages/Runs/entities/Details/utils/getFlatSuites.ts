import { ISuiteInGroupedRun } from '@Entities/runs/models';
import { ITestCase } from '@Entities/test-case/models';
import flatMap from 'lodash/flatMap';

export const getFlatSuites = (suites?: ISuiteInGroupedRun[]): Record<string, ITestCase[]> => {
    if (!suites) return {}
    const flatten = (suites: ISuiteInGroupedRun[]): ISuiteInGroupedRun[] => {
        return flatMap(suites, (suite) => [suite, ...flatten(suite.children || [])]);
    };

    return flatten(suites).reduce((acc, suite) => {
        acc[suite.suite_id] = suite.cases;

        return acc;
    }, {} as Record<string, ITestCase[]>);
};

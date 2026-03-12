import { ITreeListItem } from '@Components/TreeList/models.ts';
import { ISuite } from '@Entities/suite/models';
import map from 'lodash/map';
import reduce from 'lodash/reduce';

export function treeSuiteAdapter (suites?: ISuite[], parentSuite?: ISuite): ITreeListItem[] {
    return map(suites, (suite) => {

        const children = suite.children ? treeSuiteAdapter(suite.children, suite) : [];
        const caseCount = suite?.cases ? suite.cases.length : 0;

        //@ts-ignore
        const childrenCaseCount = reduce(children, (sum, child) => sum + child?.count, 0);

        const parentSuiteItem: ITreeListItem | null = parentSuite
            ? {
                title: parentSuite.name,
                key: parentSuite.suite_id,
                count: parentSuite.cases ? parentSuite.cases.length : 0,
                children: [],
                parent_suite: null,
                suite: parentSuite
            }
            : null;

        return {
            title: suite.name,
            key: suite.suite_id,
            value: suite.suite_id,
            count: caseCount + childrenCaseCount,
            children: children,
            parent_suite: parentSuiteItem,
            selfCount: caseCount,
            suite
        };
    });
}

import { ISuite } from '@Entities/suite/models';

interface IFindSuiteResult {
    suite: ISuite | null;
    parentIds: string[]; // Массив всех parent_id от непосредственного родителя до корня
}

export function findSuiteWithAllParents (suites: ISuite[], targetSuiteId: string): IFindSuiteResult {
    let result: IFindSuiteResult = { suite: null, parentIds: [] };

    function traverse (node: ISuite, currentParentIds: string[]): boolean {
        if (node.suite_id === targetSuiteId) {
            result.suite = node;
            result.parentIds = currentParentIds;

            return true;
        }

        if (node.children) {
            const newParentIds = [...currentParentIds, node.suite_id];

            for (const child of node.children) {
                if (traverse(child, newParentIds)) {
                    return true;
                }
            }
        }

        return false;
    }

    for (const suite of suites) {
        if (traverse(suite, [])) {
            break;
        }
    }

    return result;
}

export function findSuiteByCaseId (suites: ISuite[], caseId: string): ISuite | undefined {
    // Проходим по каждому сьюту на текущем уровне вложенности
    for (const suite of suites) {
        const hasCase = suite.cases.some((testCase) => testCase.case_id === caseId);

        if (hasCase) {
            return suite;
        }

        if (suite.children && suite.children.length > 0) {
            const foundInChild = findSuiteByCaseId(suite.children, caseId);

            if (foundInChild) {
                return foundInChild;
            }
        }
    }

    // Если прошли все сьюты на всех уровнях и ничего не нашли, возвращаем undefined
    return undefined;
}

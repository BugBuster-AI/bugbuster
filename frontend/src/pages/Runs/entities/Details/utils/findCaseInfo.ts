import { ISuiteInGroupedRun, ITestCaseInGroupedRun } from '@Entities/runs/models';
import find from 'lodash/find';

export interface ISearchCaseResult {
    suites: string[];
    currentSuite: ISuiteInGroupedRun;
    case: ITestCaseInGroupedRun;
}

export function findCaseInGroupRun (
    suites: ISuiteInGroupedRun[],
    caseId: string
): ISearchCaseResult | null {
    let result: ISearchCaseResult | null = null;

    // Рекурсивная функция для поиска кейса и построения пути сьютов
    const searchRecursive = (
        suite: ISuiteInGroupedRun,
        parentSuites: string[]
    ): boolean => {
        // Проверяем кейсы в текущем сьюте
        const foundCase = find(suite.cases, { group_run_case_id: caseId });

        if (foundCase) {
            result = {
                suites: [...parentSuites, suite.suite_id],
                currentSuite: suite,
                case: foundCase,
            };

            return true;
        }

        // Рекурсивно проверяем дочерние сьюты
        for (const childSuite of suite.children) {
            if (searchRecursive(childSuite, [...parentSuites, suite.suite_id])) {
                return true;
            }
        }

        return false;
    };

    // Ищем в каждом корневом сьюте
    for (const rootSuite of suites) {
        if (searchRecursive(rootSuite, [])) {
            break;
        }
    }

    return result;
}

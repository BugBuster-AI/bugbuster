import { ITreeListItem } from '@Components/TreeList/models.ts';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { ISuite } from '@Entities/suite/models';
import { ETestCaseType } from '@Entities/test-case/models';
import { ICaseWithExecution } from '@Features/runs/create-run-from-cases/store';
import forEach from 'lodash/forEach';
import map from 'lodash/map';
import reduce from 'lodash/reduce';
import { IReturnTypeGetCases } from './models';

export interface ITreeListItemWithTotal extends Omit<ITreeListItem, 'parent_suite' | 'children'> {
    totalCaseCount: number;
    selectedCaseCount: number;
    totalSelectedCaseCount: number;
    children?: ITreeListItemWithTotal[]
}

const filterCasesByMode = <T extends { type?: ETestCaseType }>(
    cases: T[],
    executionMode: EExecutionMode
): T[] =>
        (executionMode === EExecutionMode.SEQUENTIAL
            ? cases.filter((c) => c.type === ETestCaseType.automated)
            : cases)

export function treeSuiteAdapterWithTotal (
    suites?: ISuite[],
    selectedCases?: Record<string, ICaseWithExecution[]>,
    executionMode: EExecutionMode = EExecutionMode.PARALLEL
): ITreeListItemWithTotal[] {
    return map(suites, (suite) => {

        const children = suite.children ? treeSuiteAdapterWithTotal(suite.children, selectedCases, executionMode) : [];
        const availableCases = filterCasesByMode(suite?.cases ?? [], executionMode)
        const caseCount = availableCases.length;

        // Считаем количество кейсов в дочерних сьютах
        const childrenCaseCount = reduce(children, (sum, child) => sum + (child?.count || 0), 0);

        // Общее количество кейсов в текущем сьюте и всех его дочерних сьютах
        const totalCaseCount = caseCount + childrenCaseCount;

        // Количество выбранных кейсов в текущем сьюте (filtered by executionMode)
        const selectedCaseCount = selectedCases && suite.suite_id in selectedCases
            ? selectedCases[suite.suite_id].filter((c) => c.executionMode === executionMode).length
            : 0;

        // Сумма выбранных кейсов во всех вложенных сьютах
        const totalSelectedCaseCount =
            reduce(children, (sum, child) => sum + (child?.totalSelectedCaseCount || 0), selectedCaseCount);

        return {
            title: suite.name,
            key: suite.suite_id,
            value: suite.suite_id,
            count: totalCaseCount, // Используем totalCaseCount вместо caseCount + childrenCaseCount
            children: children,
            selfCount: caseCount, // Количество кейсов только в текущем сьюте
            totalCaseCount: totalCaseCount, // Общее количество кейсов в текущем сьюте и всех его дочерних сьютах
            selectedCaseCount: selectedCaseCount, // Количество выбранных кейсов в текущем сьюте
            totalSelectedCaseCount: totalSelectedCaseCount,
            suite
        };
    });
}

/**
 * Рекурсивно собирает все кейсы и ID сьютов из дерева
 */
export function getAllCasesAndSuites (
    suite: ISuite, 
    executionMode: EExecutionMode = EExecutionMode.PARALLEL): IReturnTypeGetCases 
{
    const cases: Record<string, ICaseWithExecution[]> = {
        [suite.suite_id]: map(filterCasesByMode(suite.cases ?? [], executionMode), (item) => ({
            id: item.case_id,
            executionMode,
            caseData: item
        }))
    };
    const suiteKeys = [suite.suite_id];

    forEach(suite?.children, (childSuite) => {
        const childData = getAllCasesAndSuites(childSuite, executionMode);

        Object.assign(cases, childData.cases);
        suiteKeys.push(...childData.suiteKeys);
    });

    return { cases, suiteKeys };
}

/**
 * Собирает все кейсы из дерева сьютов
 */
export function collectAllCasesFromTree (
    treeData: ITreeListItemWithTotal[], 
    executionMode: EExecutionMode = EExecutionMode.PARALLEL): Record<string, ICaseWithExecution[]> 
{
    const allCases: Record<string, ICaseWithExecution[]> = {};

    const collectRecursively = (item: ITreeListItemWithTotal) => {
        allCases[item.suite.suite_id] = map(
            filterCasesByMode(item.suite.cases ?? [], executionMode),
            (caseItem) => ({
                id: caseItem.case_id,
                executionMode,
                caseData: caseItem
            })
        );

        forEach(item.children, (childItem) => {
            collectRecursively(childItem);
        });
    };

    forEach(treeData, (item) => {
        collectRecursively(item);
    });

    return allCases;
}

/**
 * Собирает все ID сьютов из дерева
 */
export function collectAllSuiteIds (treeData: ITreeListItemWithTotal[]): string[] {
    const suiteIds: string[] = [];

    const collectRecursively = (item: ITreeListItemWithTotal) => {
        suiteIds.push(item.suite.suite_id);
        forEach(item.children, (childItem) => {
            collectRecursively(childItem);
        });
    };

    forEach(treeData, (item) => {
        collectRecursively(item);
    });

    return suiteIds;
}

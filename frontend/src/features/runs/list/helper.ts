import { IGroupedRun, IRun, ISuiteInGroupedRun } from '@Entities/runs/models';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { IStreamsStatList } from '@Entities/stream/models';
import { ITestCase } from '@Entities/test-case/models';
import { ICaseWithExecution } from '@Features/runs/create-run-from-cases/store';
import get from 'lodash/get';
import map from 'lodash/map';

export const adaptRunData = (data?: {
    items: IGroupedRun[],
}, streams?: IStreamsStatList['group_run_statistics']): IRun[] => {
    if (!data) {
        return []
    }
    const items = data.items

    return map(items, (item) => {

        const streamsData = get(streams, item.group_run_id, null)
        const streamsTitle = streamsData ? `${streamsData?.active_streams}/${streamsData?.total_streams}` : '-'

        return {
            // TODO: Author
            name: item.name,
            parallel_exec: streamsData?.total_streams || 0,
            author: '-',
            streams: streamsTitle,
            date: item.created_at,
            status: item.status,
            stats: item.stats,
            time: item.complete_time || 0,
            deadline: item.deadline,
            id: item.group_run_id,
            data: item,
            use_parallel_flag: item?.use_parallel_flag
        } as IRun
    })
}

export const transformCases = (groupedRun?: IGroupedRun): Record<string, ICaseWithExecution[]> => {
    if (!groupedRun) return {}
    const cases: Record<string, ICaseWithExecution[]> = {};

    const collectCases = (suites: ISuiteInGroupedRun[]) => {
        suites.forEach((suite) => {
            if (suite.cases) {
                cases[suite.suite_id] = suite.cases.map((testCase) => ({
                    id: testCase.case_id,
                    executionMode: EExecutionMode.PARALLEL,
                    caseData: testCase as unknown as ITestCase,
                }));
            }
            if (suite.children) {
                collectCases(suite.children);
            }
        });
    };

    collectCases(groupedRun.parallel ?? groupedRun.suites ?? []);

    // Добавляем sequential-кейсы под специальным ключом
    if (groupedRun.sequential?.length) {
        cases['__sequential__'] = groupedRun.sequential.map((item) => ({
            id: item.case_id,
            executionMode: EExecutionMode.SEQUENTIAL,
            executionOrder: item.execution_order,
            caseData: item.case as unknown as ITestCase,
        }));
    }

    return cases;
};

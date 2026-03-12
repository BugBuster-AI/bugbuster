import { ReloadOutlined } from '@ant-design/icons';
import { IRunStats, ISuiteInGroupedRun } from '@Entities/runs/models';
import { ITestCase } from '@Entities/test-case/models';
import { StartAutomated } from '@Features/runs/start-automated';
import { StartManual } from '@Features/runs/start-manual';
import { SuiteTableTree } from '@Pages/Runs/entities/Details/components/SuiteTableTree';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Button, Dropdown, Flex, Menu, Typography } from 'antd';
import flatMap from 'lodash/flatMap';
import size from 'lodash/size';
import values from 'lodash/values';
import { ReactElement, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

const sumStats = (stats: IRunStats): number =>
    stats.untested +
    stats.passed +
    stats.failed +
    stats.blocked +
    stats.invalid +
    stats.retest +
    stats.in_progress +
    stats.in_queue +
    stats.stopped +
    (stats.stop_in_progress ?? 0) +
    (stats.preparation ?? 0) +
    (stats.after_step_failure ?? 0)

const completedFromStats = (stats: IRunStats): number =>
    stats.passed +
    stats.failed +
    stats.blocked +
    stats.invalid +
    stats.stopped +
    (stats.after_step_failure ?? 0)

const aggregateStats = (suites: ISuiteInGroupedRun[]): { total: number; completed: number } => {
    /* Считаем только по leaf-сьютам (с кейсами), чтобы не задваивать */
    const getLeafStats = (s: ISuiteInGroupedRun[]): IRunStats[] => {
        return s.flatMap((suite) => {
            if (size(suite.children) > 0) return getLeafStats(suite.children)

            return [suite.stats]
        })
    }

    const leafStats = getLeafStats(suites)
    const total = leafStats.reduce((acc, st) => acc + sumStats(st), 0)
    const completed = leafStats.reduce((acc, st) => acc + completedFromStats(st), 0)

    return { total, completed }
}

export const ParallelSection = (): ReactElement | null => {
    const { t } = useTranslation()
    const runItem = useGroupedRunStore((state) => state.runItem)
    const selectedCases = useGroupedRunStore((state) => state.selectedCases)
    const setSelectedCases = useGroupedRunStore((state) => state.setSelectedCase)
    const runStreams = useGroupedRunStore((state) => state.streams)

    const parallel = runItem?.parallel ?? []

    const { total, completed } = useMemo(() => aggregateStats(parallel), [parallel])

    const allCasesSize = useMemo(
        () => size(values(selectedCases).flatMap((v) => v)),
        [selectedCases]
    )

    const getCaseIds = (key: keyof ITestCase = 'group_run_case_id') =>
        flatMap(selectedCases, (items) => items.map((i) => i[key] as string))

    const isAvailableStreams = runStreams && runStreams.total_streams > 0

    if (!size(parallel)) return null

    return (
        <Flex gap={ 8 } vertical>
            <Flex align="center" justify="space-between">
                <Typography.Title level={ 5 } style={ { margin: 0 } }>
                    {t('group_run.parallel')}
                </Typography.Title>
                <Flex align="center" gap={ 8 }>
                    <Typography.Text type="secondary">
                        {completed}/{total} {t('group_run.completed')}
                    </Typography.Text>

                    <Dropdown
                        align={ { points: ['t', 'bl'] } }
                        disabled={ !allCasesSize }
                        dropdownRender={ () => (
                            <Menu activeKey="null" style={ { width: 200 } }>
                                <StartManual
                                    groupId={ runItem?.group_run_id! }
                                    renderButton={ ({ onClick, label }) => (
                                        <Menu.Item onClick={ () => { onClick(); setSelectedCases(undefined) } }>
                                            {label}
                                        </Menu.Item>
                                    ) }
                                    runIds={ getCaseIds() }
                                />
                                <StartAutomated
                                    available={ isAvailableStreams }
                                    groupId={ runItem?.group_run_id! }
                                    renderButton={ ({ onClick, label }) => (
                                        <Menu.Item onClick={ () => { onClick(); setSelectedCases(undefined) } }>
                                            {label}
                                        </Menu.Item>
                                    ) }
                                    runIds={ getCaseIds() }
                                />
                            </Menu>
                        ) }
                        trigger={ ['click'] }
                    >
                        <Button
                            disabled={ !allCasesSize }
                            icon={ <ReloadOutlined/> }
                            size="small"
                        >
                            {t('grouped_run.buttons.rerun')}
                        </Button>
                    </Dropdown>
                </Flex>
            </Flex>

            <SuiteTableTree/>
        </Flex>
    )
}

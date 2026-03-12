import { ReloadOutlined } from '@ant-design/icons';
import { StatusBadge } from '@Common/components';
import { PROGRESS_STATUSES } from '@Common/consts/run';
import { URL_QUERY_KEYS } from '@Common/consts/searchParams.ts';
import { ERunStatus, ISequentialRunCase } from '@Entities/runs/models';
import { useTestCaseStore } from '@Entities/test-case';
import { ITestCase } from '@Entities/test-case/models';
import { StartAutomated } from '@Features/runs/start-automated';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Button, Checkbox, Flex, Table, Tag, Tooltip, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import includes from 'lodash/includes';
import size from 'lodash/size';
import { ReactElement, useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

const FINISHED_STATUSES: ERunStatus[] = [
    ERunStatus.PASSED,
    ERunStatus.FAILED,
    ERunStatus.BLOCKED,
    ERunStatus.INVALID,
    ERunStatus.STOPPED,
    ERunStatus.AFTER_STEP_FAILURE,
]

const ACTIVE_STATUSES: ERunStatus[] = [
    ...PROGRESS_STATUSES,
    ERunStatus.UNTESTED,
    ERunStatus.RETEST,
]

const isSectionDone = (cases: ISequentialRunCase[]): boolean =>
    cases.every((c) => !includes(ACTIVE_STATUSES, c.case.actual_status))

const isRunFinished = (status?: ERunStatus): boolean =>
    !!status && !includes(PROGRESS_STATUSES, status)

const canRetestSequential = (cases: ISequentialRunCase[], runStatus?: ERunStatus): boolean =>
    isSectionDone(cases) || isRunFinished(runStatus)

/* ─── Main Component ─── */

export const SequentialSection = (): ReactElement | null => {
    const { t } = useTranslation()
    const runItem = useGroupedRunStore((state) => state.runItem)
    const setOpenedCaseId = useGroupedRunStore((state) => state.setOpenedCaseId)
    const openedCaseId = useGroupedRunStore((state) => state.openedCaseId)
    const setDrawerOpen = useGroupedRunStore((state) => state.setDrawerOpen)
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)

    const runStreams = useGroupedRunStore((state) => state.streams)
    const [selectedIds, setSelectedIds] = useState<string[]>([])
    const [, updateSearchParams] = useSearchParams()

    /*
     * Берём данные напрямую из стора — никакого локального состояния списка,
     * чтобы обновления статусов (polling) сразу отражались в таблице
     */
    const currentItems = runItem?.sequential ?? []

    const runStatus = runItem?.status
    const retestAvailable = canRetestSequential(currentItems, runStatus)

    const completedCount = useMemo(
        () => currentItems.filter((c) => includes(FINISHED_STATUSES, c.case.actual_status)).length,
        [currentItems]
    )

    // Только завершённые кейсы можно ретестировать
    const retestableIds = useMemo(
        () => currentItems
            .filter((c) => includes(FINISHED_STATUSES, c.case.actual_status))
            .map((c) => c.group_run_case_id),
        [currentItems]
    )

    const isAllSelected =
        retestableIds.length > 0 && retestableIds.every((id) => selectedIds.includes(id))
    const isIndeterminate =
        selectedIds.length > 0 && !isAllSelected

    const handleSelectAll = useCallback((checked: boolean) => {
        setSelectedIds(checked ? retestableIds : [])
    }, [retestableIds])

    const handleSelectRow = useCallback((id: string, checked: boolean) => {
        setSelectedIds((prev) =>
            (checked ? [...prev, id] : prev.filter((x) => x !== id))
        )
    }, [])

    const openCase = useCallback((item: ISequentialRunCase) => {
        setDrawerOpen(true)
        setCurrentCase(item.case as unknown as ITestCase)
        setOpenedCaseId(item.group_run_case_id)
        updateSearchParams((prev) => {
            prev.set(URL_QUERY_KEYS.CASE_ID, item.group_run_case_id)

            return prev
        })
    }, [setCurrentCase, setOpenedCaseId, setDrawerOpen, updateSearchParams])

    if (!size(currentItems)) return null

    const columns: ColumnsType<ISequentialRunCase> = [
        {
            key: 'checkbox',
            width: 40,
            title: (
                <Tooltip
                    title={ !retestAvailable ? t('group_run.retest_locked_sequential') : undefined }
                >
                    <Checkbox
                        checked={ isAllSelected }
                        disabled={ !retestAvailable || retestableIds.length === 0 }
                        indeterminate={ isIndeterminate }
                        onChange={ (e) => handleSelectAll(e.target.checked) }
                        onClick={ (e) => e.stopPropagation() }
                    />
                </Tooltip>
            ),
            render: (_v, record) => {
                const isRetestable = includes(FINISHED_STATUSES, record.case.actual_status)

                return (
                    <Checkbox
                        checked={ selectedIds.includes(record.group_run_case_id) }
                        disabled={ !retestAvailable || !isRetestable }
                        onChange={ (e) => handleSelectRow(record.group_run_case_id, e.target.checked) }
                        onClick={ (e) => e.stopPropagation() }
                    />
                )
            },
        },
        {
            key: 'order',
            title: '#',
            width: 48,
            render: (_v, _r, index) => (
                <Tag color="blue">{index + 1}</Tag>
            ),
        },
        {
            key: 'status',
            title: t('group_run.status'),
            width: 140,
            render: (_v, record) => (
                <StatusBadge status={ record.case.actual_status }/>
            ),
        },
        {
            key: 'name',
            title: t('group_run.case_name'),
            dataIndex: ['case', 'name'],
            ellipsis: true,
        },
        {
            key: 'suite_path',
            title: t('group_run.suite_path'),
            dataIndex: 'suite_path',
            ellipsis: true,
            render: (val: string) => (
                <Typography.Text style={ { fontSize: 12 } } type="secondary">
                    {val}
                </Typography.Text>
            ),
        },        
    ]

    const isAvailableStreams = runStreams && runStreams?.total_streams > 0

    return (
        <Flex gap={ 8 } vertical>
            <Flex align="center" justify="space-between">
                <Typography.Title level={ 5 } style={ { margin: 0 } }>
                    {t('group_run.sequential')}
                </Typography.Title>
                <Flex align="center" gap={ 8 }>
                    <Typography.Text type="secondary">
                        {completedCount}/{size(currentItems)} {t('group_run.completed')}
                    </Typography.Text>

                    <Tooltip
                        title={
                            !retestAvailable
                                ? t('group_run.retest_locked_sequential')
                                : undefined
                        }
                    >
                        <StartAutomated
                            available={ !!isAvailableStreams }
                            groupId={ runItem?.group_run_id! }
                            onSuccess={ () => setSelectedIds([]) }
                            renderButton={ ({ onClick }) => (
                                <Button
                                    disabled={ !retestAvailable || selectedIds.length === 0 }
                                    icon={ <ReloadOutlined/> }
                                    onClick={ onClick }
                                    size="small"
                                >
                                    {t('grouped_run.buttons.rerun')} ({selectedIds.length})
                                </Button>
                            ) }
                            runIds={ selectedIds }
                        />
                    </Tooltip>
                </Flex>
            </Flex>

            <Table<ISequentialRunCase>
                columns={ columns }
                dataSource={ currentItems }
                onRow={ (record) => ({
                    onClick: () => openCase(record),
                    style: {
                        cursor: 'pointer',
                        background:
                            record.group_run_case_id === openedCaseId
                                ? 'rgba(0, 0, 0, 0.02)'
                                : undefined,
                    },
                }) }
                pagination={ false }
                rowKey={ (r) => r.group_run_case_id }
                scroll={ { y: 500 } }
                size="small"
                virtual
            />
        </Flex>
    )
}

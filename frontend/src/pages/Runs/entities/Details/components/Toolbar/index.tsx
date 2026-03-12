import { CheckOutlined, DeleteOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { DebouncedSearch } from '@Components/DebouncedSearch';
import { ERunStatus } from '@Entities/runs/models';
import { useRemoveRunFromGroup } from '@Entities/runs/queries/mutations.ts';
import { ETestCaseType, ITestCase } from '@Entities/test-case/models';
import { AddRunResult } from '@Pages/Runs/entities/Details/components/Drawer/components/Execution/components';
import StatusFilter from '@Pages/Runs/entities/Details/components/FilterDropdown';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Button, Flex, Tooltip } from 'antd';
import flatMap from 'lodash/flatMap';
import size from 'lodash/size';
import values from 'lodash/values';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

const FINISHED_STATUS =
    [
        ERunStatus.PASSED,
        ERunStatus.FAILED,
        ERunStatus.BLOCKED,
        ERunStatus.INVALID,
        ERunStatus.STOPPED,
        ERunStatus.UNTESTED
    ]

export const Toolbar = () => {
    const [fastStatusOpen, setFastStatusOpen] = useState<boolean>(false)
    const selectedCases = useGroupedRunStore((state) => state.selectedCases)
    const runItem = useGroupedRunStore((state) => state.runItem)
    const setSelectedCases = useGroupedRunStore((state) => state.setSelectedCase)
    const setSearch = useGroupedRunStore((state) => state.setSearch)
    const { mutateAsync } = useRemoveRunFromGroup()
    const { t } = useTranslation()

    const allCases = useMemo(() => values(selectedCases)?.reduce((acc, val) => {
        return [...acc, ...val]
    }, []), [selectedCases])

    const allCasesSize = size(allCases)

    const getCaseIds = (key?: (keyof ITestCase | false)) => {
        const caseKey = key === false ? undefined : (key || 'group_run_case_id')

        return flatMap(selectedCases, (item) => item.map((i) => (caseKey ? i?.[caseKey] : i)))
    }

    const removeRun = async () => {
        const caseIds = getCaseIds()

        await asyncHandler(mutateAsync.bind(null, {
            runId: runItem?.group_run_id!,
            case_ids: caseIds as string[]
        }),
        { onSuccess: () => setSelectedCases(undefined) }
        )
    }

    const handleSearch = (value: string) => {
        setSearch(value)
    }

    const hasManualUnfinished = allCases.some(
        (testCase) =>
            testCase.case_type_in_run === ETestCaseType.manual &&
            testCase.actual_status && !FINISHED_STATUS.includes(testCase.actual_status)
    );

    return (
        <Flex align={ 'center' } flex={ 1 } justify={ 'space-between' }>
            {fastStatusOpen && <AddRunResult

                onClose={ setFastStatusOpen.bind(null, false) }
                open={ fastStatusOpen }
                runIds={ getCaseIds('actual_run_id') as string[] }
            />}
            <Flex align={ 'center' } gap={ 16 }>
                <DebouncedSearch onChange={ handleSearch }/>

                <StatusFilter/>
            </Flex>

            <Flex gap={ 8 }>
                <Tooltip
                    title={
                        Boolean(!hasManualUnfinished || !allCasesSize) && t('group_run.submit.warning_disabled') }
                >
                    <Button
                        disabled={ !allCasesSize || !hasManualUnfinished }
                        icon={ <CheckOutlined/> }
                        onClick={ setFastStatusOpen.bind(null, true) }>
                        {t('grouped_run.buttons.submit')}
                    </Button>
                </Tooltip>

                <ConfirmButton
                    buttonLabel={ t('grouped_run.buttons.remove') }
                    buttonProps={ {
                        type: 'default',
                        variant: 'solid',
                        disabled: !allCasesSize,
                    } }
                    icon={ <DeleteOutlined/> }
                    modalProps={ {
                        centered: true,
                        onOk: removeRun,
                        title: t('group_run.remove_case.title'),
                        okText: t('group_run.remove_case.ok'),
                        cancelText: t('group_run.remove_case.cancel'),
                    } }
                    closeAfterOk
                >
                    <div>
                        {t('group_run.remove_case.body', { count: size(getCaseIds()) })}
                    </div>
                </ConfirmButton>
            </Flex>
        </Flex>
    )
}

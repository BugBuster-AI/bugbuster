import SquareIcon from '@Assets/icons/square.svg?react'
import { asyncHandler } from '@Common/utils';
import { ERunStatus } from '@Entities/runs/models';
import { useTestCaseStore } from '@Entities/test-case';
import { ETestCaseType } from '@Entities/test-case/models';
import { useStopCaseRunning } from '@Entities/test-case/queries';
import { StartAutomated } from '@Features/runs/start-automated';
import { StartManual } from '@Features/runs/start-manual';
import { useGroupDrawerContext } from '@Pages/Runs/entities/Details/components/Drawer/context';
import { ECaseState } from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Button, Flex } from 'antd';
import head from 'lodash/head';
import { useTranslation } from 'react-i18next';

export const TopDrawerButtons = () => {
    const { t } = useTranslation()
    const currentCase = useTestCaseStore((state) => state.currentCase)
    const setActiveKey = useTestCaseStore((state) => state.setActiveDrawerKey)
    const currentRun = useGroupedRunStore((state) => state.runItem)
    const { currentCaseType, setLoading, setCurrentCaseType } = useGroupDrawerContext()
    const { mutateAsync, isPending: stopIsPending } = useStopCaseRunning()
    const runStreams = useGroupedRunStore((state) => state.streams)
    const isAvailableStreams = runStreams && runStreams?.total_streams > 0
    const updateCurrentCase = useTestCaseStore((state) => state.updateCurrentCase)
    const isManual = currentCaseType === ECaseState.MANUAL_EDIT

    const handleManualClick = (ids: string[]) => {
        setActiveKey('1')
        const actualRunId = head(ids)

        setCurrentCaseType(ECaseState.MANUAL_EDIT)

        // оптимистичный апдейт
        updateCurrentCase({
            actual_run_id: actualRunId,
            case_type_in_run: ETestCaseType.manual,
            actual_status: ERunStatus.IN_QUEUE
        })
    }

    const handleAutoClick = (ids: string[]) => {
        setActiveKey('1')
        const actualRunId = head(ids)

        setCurrentCaseType(ECaseState.AUTO_IN_PROGRESS)

        // оптимистичный апдейт
        updateCurrentCase({
            actual_run_id: actualRunId,
            case_type_in_run: ETestCaseType.automated,
            actual_status: ERunStatus.IN_QUEUE
        })
    }

    const handleStop = async () => {
        if (!currentRun) return

        await asyncHandler(mutateAsync.bind(null, currentCase?.actual_run_id!), {
            successMessage: t('test_case_run.stopped'),
        })

        updateCurrentCase({
            actual_status: ERunStatus.STOP_IN_PROGRESS
        })
    }

    if (currentCaseType === ECaseState.AUTO_IN_PROGRESS) {
        return (
            <Flex align={ 'center' } gap={ 8 } style={ { marginBottom: 8 } }>
                <Button
                    icon={ <SquareIcon style={ { strokeWidth: 2, width: 16, height: 16 } }/> } 
                    loading={ currentCase?.actual_status === ERunStatus.STOP_IN_PROGRESS || stopIsPending }
                    onClick={ handleStop }>
                    {t('running_page.buttons.stop')}
                </Button>
            </Flex>
        )
    }

    return (
        <Flex align={ 'center' } gap={ 8 } style={ { marginBottom: 8 } }>
            {!isManual &&
                <StartManual
                    groupId={ currentRun?.group_run_id! }
                    onSuccess={ handleManualClick }
                    runIds={ [currentCase?.group_run_case_id!] }
                    setLoading={ setLoading }
                />
            }
            {currentCase?.type === ETestCaseType.automated && !isManual &&
                <StartAutomated
                    available={ isAvailableStreams }
                    groupId={ currentRun?.group_run_id! }
                    onSuccess={ handleAutoClick }
                    runIds={ [currentCase?.group_run_case_id!] }
                />
            }
        </Flex>
    )
}

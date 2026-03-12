import { ERunStatus } from '@Entities/runs/models';
import { useTestCaseStore } from '@Entities/test-case';
import { SetFinalTestStatus } from '@Features/test-case/set-final-statuses';
import {
    UntestedSteps
} from '@Pages/Runs/entities/Details/components/Drawer/components/Execution/components/UntestedSteps';
import { useGroupDrawerContext } from '@Pages/Runs/entities/Details/components/Drawer/context';
import { ECaseState } from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Flex } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AddRunResult, FinishedCase, InProgressCase, ManualEdit } from './components';
import { InfoField } from './InfoField.tsx';

export const ExecutionDrawer = () => {
    const [fastStatusOpen, setFastStatusOpen] = useState<ERunStatus | undefined>(undefined)
    const testCase = useTestCaseStore((state) => state.currentCase)
    const caseSuite = useGroupedRunStore((state) => state.currentCaseSuite)
    const runItem = useGroupedRunStore((state) => state.runItem)
    const updateCurrentCase = useTestCaseStore((state) => state.updateCurrentCase)
    const { setCurrentCaseType } = useGroupDrawerContext()
    const { currentCaseType } = useGroupDrawerContext()
    const { t } = useTranslation()

    const handleSetStatus = (status?: ERunStatus) => {
        setFastStatusOpen(status)
    }

    const handleAddResultSuccess = (status: ERunStatus) => {
        setCurrentCaseType(ECaseState.AUTO_FINISH)

        updateCurrentCase({
            actual_status: status,
            status
        })
    }

    const isProgress = currentCaseType === ECaseState.AUTO_IN_PROGRESS
    const isFinished = currentCaseType === ECaseState.AUTO_FINISH || currentCaseType === ECaseState.MANUAL_FINISH
    const isManualEdit = currentCaseType === ECaseState.MANUAL_EDIT
    const isUntested = currentCaseType === ECaseState.UNTESTED

    return <Flex style={ { height: '100%' } } vertical>
        {fastStatusOpen && (
            <AddRunResult
                defaultStatus={ fastStatusOpen }
                onClose={ setFastStatusOpen.bind(null, undefined) }
                onSuccess={ handleAddResultSuccess }
                open={ !!fastStatusOpen }
            />
        )}

        {isManualEdit && (
            <SetFinalTestStatus
                onChange={ handleSetStatus }
                resettable={ false }
                value={ fastStatusOpen }
            />)
        }

        <Flex vertical>
            <InfoField fieldName={ t('group_run.execution.suite_description') } value={ caseSuite?.suite_description }/>
            <InfoField fieldName={ t('group_run.execution.description') } value={ testCase?.description }/>
            <InfoField fieldName={ t('group_run.execution.variables') } value={ runItem?.variables }/>
            <InfoField fieldName={ t('group_run.execution.url') } value={ testCase?.url }/>
        </Flex>

        <div style={ { flex: 1, width: '100%', marginTop: '10px', paddingBottom: 42 } }>
            {isUntested && <UntestedSteps/>}
            {isProgress && <InProgressCase/>}
            {isFinished && <FinishedCase/>}
            {isManualEdit && <ManualEdit/>}
        </div>
    </Flex>
}

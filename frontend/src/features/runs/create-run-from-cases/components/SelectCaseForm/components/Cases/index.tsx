import { EExecutionMode } from '@Entities/runs/models/enum';
import { CaseTable } from '@Entities/test-case';
import { ETestCaseType } from '@Entities/test-case/models';
import { ICaseWithExecution, useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { Empty, Flex, Typography } from 'antd';
import map from 'lodash/map';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    executionMode: EExecutionMode
}

export const CasesList = ({ executionMode }: IProps) => {
    const { t } = useTranslation()
    const currentSuite = useCreateRunStore((state) => state.currentSuite)
    const setTempCases = useCreateRunStore((state) => state.setTempCases)
    const tempCases = useCreateRunStore((state) => state.tempCases)
    const selectedCases = useCreateRunStore((state) => state.selectedCaseId)

    const handleSelect = (selectedKeys: string[]) => {
        if (!currentSuite) return

        const existingCases = tempCases[currentSuite.suite_id] || []
        
        const casesFromOtherModes = existingCases.filter((c) => c.executionMode !== executionMode)
        
        const newCasesForCurrentMode = selectedKeys
            .map((id) => {
                const caseData = (currentSuite.cases || []).find((c) => c.case_id === id)

                if (!caseData) return null

                return {
                    id,
                    executionMode,
                    caseData
                }
            })
            .filter((c): c is ICaseWithExecution => c !== null)
        
        const merged = [...casesFromOtherModes, ...newCasesForCurrentMode]

        setTempCases({ [currentSuite.suite_id]: merged })
    }

    useEffect(() => {
        setTempCases(selectedCases)
    }, [selectedCases]);

    useEffect(() => {
        return () => {
            setTempCases(undefined)
        }
    }, []);

    const currentCases = currentSuite ? (tempCases?.[currentSuite?.suite_id] || []) : []
    // Show only cases with the current execution mode
    const currentCaseIds = map(
        currentCases.filter((c: ICaseWithExecution) => c.executionMode === executionMode),
        'id'
    )

    // Filter out cases that are selected in other execution modes
    const casesSelectedInOtherModes = map(
        currentCases.filter((c: ICaseWithExecution) => c.executionMode !== executionMode),
        'id'
    )
    
    // Filter data to exclude cases selected in other modes
    const availableData = (currentSuite?.cases || []).filter(
        (c) => !casesSelectedInOtherModes.includes(c.case_id)
            && (executionMode !== EExecutionMode.SEQUENTIAL || c.type === ETestCaseType.automated)
    )

    if (!currentSuite) return (
        <Empty
            description={ t('create_run.no_selected_item') }
            style={ { alignSelf: 'center', margin: '0 auto' } }
        />
    )

    return (
        <Flex gap={ 16 } vertical>
            <Typography.Title level={ 5 }>{currentSuite.name}</Typography.Title>
            <CaseTable
                data={ availableData }
                draggable={ false }
                onSelect={ handleSelect }
                selectedKeys={ currentCaseIds }
            />
        </Flex>
    )
}

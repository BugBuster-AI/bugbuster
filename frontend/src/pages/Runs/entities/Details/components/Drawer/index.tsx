import { EFromRedirect } from '@Common/types';
import { useTestCaseStore } from '@Entities/test-case';
import { CodeTab } from '@Features/test-case/drawer/components/CodeTab';
import { TestCaseDrawer } from '@Features/test-case/drawer';
import drawerLayoutStyles from '@Features/test-case/drawer/index.module.scss';
import { TestCaseRunsHistory } from '@Features/test-case/runs-history';
import {
    ChangeCaseControls
} from '@Pages/Runs/entities/Details/components/Drawer/components/Execution/components/ChangeCaseControls';
import { GroupCaseDrawerContext } from '@Pages/Runs/entities/Details/components/Drawer/context';
import { useInvalidateController } from '@Pages/Runs/entities/Details/components/Drawer/hooks/invalidateController.ts';
import { ECaseState, getCaseState } from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils';
import { findCaseById } from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils/find-case.ts';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { TabsProps } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { TopDrawerButtons, ExecutionDrawer, DrawerTitle } from './components';

interface IProps {
    onClose: () => void
}

export const GroupCaseDrawer = ({ onClose }: IProps) => {
    const { t } = useTranslation()
    const [opened, setOpened] = useState(true)
    const [currentCaseType, setCurrentCaseType] = useState(ECaseState.INITIAL)
    const currentCase = useTestCaseStore((state) => state.currentCase)
    const [isLoading, setLoading] = useState(false)
    const runItem = useGroupedRunStore((state) => state.runItem)
    const openedCaseId = useGroupedRunStore((state) => state.openedCaseId)
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)
    const setCaseFetching = useGroupedRunStore((state) => state.setCaseFetching)
    const [searchParams] = useSearchParams()
    const setActiveKey = useTestCaseStore((state) => state.setActiveDrawerKey)
    const activeKey = useTestCaseStore((state) => state.activeDrawerKey)

    const handleClose = () => {
        setOpened(false)
        setCaseFetching(false)
    }

    useEffect(() => {
        if (openedCaseId) {
            // Сначала ищем в parallel дереве
            const parallelCase = findCaseById(runItem?.parallel, openedCaseId)

            if (parallelCase) {
                setCurrentCase(parallelCase)
            } else {
                // Ищем в sequential
                const seqEntry = runItem?.sequential?.find(
                    (s) => s.group_run_case_id === openedCaseId
                )

                if (seqEntry) {
                    setCurrentCase(seqEntry.case)
                } else {
                    handleClose()
                }
            }
        }
    }, [openedCaseId, runItem])


    useEffect(() => {
        if (!opened) {
            const closeTimer = setTimeout(() => {
                onClose()
            }, 200)

            return () => {
                clearTimeout(closeTimer)
            }
        }
    }, [opened]);

    useEffect(() => {
        const openHistory = searchParams.get('open') === EFromRedirect.HISTORY

        if (openHistory) {
            setActiveKey('2')
        }
    }, [searchParams]);

    useEffect(() => {
        const caseType = getCaseState(currentCase?.case_type_in_run, currentCase?.actual_status)

        setCurrentCaseType(caseType)
    }, [currentCase, runItem]);

    useInvalidateController(runItem?.group_run_id, currentCase?.actual_status)

    const drawerItems: TabsProps['items'] = useMemo(() => [
        {
            key: '1',
            label: t('drawerTabs.execution'),
            children: (
                <div className={ drawerLayoutStyles.tabPaneScroll }>
                    <ExecutionDrawer/>
                </div>
            ),
        },
        {
            key: '2',
            children: (
                <div className={ drawerLayoutStyles.tabPaneScroll }>
                    <TestCaseRunsHistory/>
                </div>
            ),
            destroyInactiveTabPane: true,
            label: t('drawerTabs.run_history'),
        },
        {
            key: '3',
            children: (
                <div className={ drawerLayoutStyles.codeTabPane }>
                    <CodeTab/>
                </div>
            ),
            destroyInactiveTabPane: true,
            label: t('drawerTabs.codegen'),
        },
    ], [t])

    const memoizedProps = useMemo(() => ({
        currentCaseType,
        isLoading,
        setCurrentCaseType,
        setLoading
    }), [currentCase, isLoading, currentCaseType])

    return (
        <GroupCaseDrawerContext.Provider value={ memoizedProps }>
            <TestCaseDrawer
                afterOpenChange={ (open) => {
                    if (!open) {
                        setCurrentCase(undefined)
                        onClose()
                    }
                } }
                bodyBottomSlot={ activeKey === '1' && <ChangeCaseControls/> }
                extraRightButtons={ null }
                items={ drawerItems }
                onClose={ handleClose }
                open={ opened }
                showCaseDescription={ false }
                titleComponent={ <DrawerTitle/> }
                underTabButtons={ <TopDrawerButtons/> }
                setSearchParamsOnChange
                setSearchParamsOnOpen
            />
        </GroupCaseDrawerContext.Provider>
    )
}

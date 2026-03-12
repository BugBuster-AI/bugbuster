import { PlusOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { useSuiteStore } from '@Entities/suite/store';
import { ITestCase } from '@Entities/test-case/models';
import { useTestCaseStore } from '@Entities/test-case/store';
import { DraggableCaseTable } from '@Features/suite/suites-control/components/RightSide/DraggableCaseTable.tsx';
import { useSuitesControlContext } from '@Features/suite/suites-control/context';
import {
    CreateFromRecords,
    DeleteButton,
    CopyButton,
    TestCaseDrawer
} from '@Features/test-case';
import { Button, Flex, Typography } from 'antd';
import filter from 'lodash/filter';
import find from 'lodash/find';
import size from 'lodash/size';
import { ReactElement, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export const RightSide = (): ReactElement => {
    const [selectedCases, setSelectedCases] = useState<string[]>([])
    const [searchParams, updateSearchParams] = useSearchParams()
    const [drawerOpen, setDrawerOpen] = useState(false)

    const token = useThemeToken()
    const navigate = useNavigate()

    const { movingCaseToSuite } = useSuitesControlContext()
    const selectedSuite = useSuiteStore((state) => state.selectedSuite)
    const loading = useSuiteStore((state) => state.loading)
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)
    const currentCase = useTestCaseStore((state) => state.currentCase)

    const currentSuiteId = selectedSuite?.suite_id || null
    const suiteName = selectedSuite?.name
    const hasSelected = size(selectedCases) > 0

    const caseTableData = useMemo(() => selectedSuite?.cases, [selectedSuite])

    const handleCreateCase = (): void => {
        const url = currentSuiteId ? `create-case?suiteId=${currentSuiteId}` : 'create-case'

        navigate(url)
    }

    const handleSelectCase = (cases: string[]) => {
        setSelectedCases(cases)
    }

    const handleClose = () => {
        setDrawerOpen(false)

        updateSearchParams((prev) => {
            prev.delete('open')
            prev.delete('caseId')

            return prev
        })
    }

    useEffect(() => {
        const caseId = searchParams.get('caseId')
        const currentCase = find(caseTableData, (item: ITestCase) => String(item.case_id) === caseId)

        if (caseId && caseTableData && currentCase) {
            setCurrentCase(currentCase)
            setDrawerOpen(true)
        }
    }, [searchParams, caseTableData]);

    useEffect(() => {
        if (caseTableData && size(selectedCases)) {
            const updatedSelectedCases = filter(selectedCases, (caseId) =>
                caseTableData.some((testCase) => testCase.case_id === caseId)
            )

            setSelectedCases(updatedSelectedCases)
        }
    }, [caseTableData])

    useEffect(() => {
        setSelectedCases([])
    }, [selectedSuite])


    const sortedData = useMemo(() => caseTableData?.sort((a, b) => a.position - b.position), [caseTableData])

    return (
        <>
            <Flex gap={ token.margin } style={ { paddingBottom: token.padding } } vertical>
                <Flex align={ 'center' } gap={ token.margin } wrap>
                    {suiteName && (
                        <Typography.Title
                            level={ 5 }
                            style={ { margin: 0 } }
                        >
                            {suiteName}
                        </Typography.Title>
                    )}

                    <Flex align={ 'center' } gap={ 8 } wrap>
                        <Button icon={ <PlusOutlined/> } onClick={ handleCreateCase }/>
                        <CreateFromRecords/>
                        <CopyButton case_id={ selectedCases } disabled={ !hasSelected }/>
                        <DeleteButton case_id={ selectedCases } disabled={ !hasSelected }/>
                    </Flex>
                </Flex>

                <DraggableCaseTable
                    data={ sortedData }
                    isLoading={ loading }
                    loadingRow={ movingCaseToSuite?.case_id }
                    onSelect={ handleSelectCase }
                    props={ {
                        //@ts-ignore
                        onRow: (props: ITestCase) => ({
                            itemKey: props.position,
                            record: props,
                            onClick: () => {
                                setCurrentCase(props)
                                setDrawerOpen(true)
                            },
                            style: {
                                background: currentCase?.case_id === props.case_id ? 'rgba(0, 0, 0, 0.02)' : undefined
                            }
                        })
                    } }
                    selectedKey={ currentSuiteId }
                    selectedKeys={ selectedCases }
                    savePaginationQueryParameters
                />
            </Flex>

            <TestCaseDrawer onClose={ handleClose } open={ drawerOpen } setSearchParamsOnOpen/>
        </>
    )
}

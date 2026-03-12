import { URL_QUERY_KEYS } from '@Common/consts/searchParams.ts';
import { DefaultCaseTable } from '@Entities/runs/components/TableSuiteRun/DefaultTable.tsx';
import { ISuiteInGroupedRun } from '@Entities/runs/models';
import { useTestCaseStore } from '@Entities/test-case';
import { ITestCase } from '@Entities/test-case/models';
import {
    findCaseById,
} from '@Pages/Runs/entities/Details/components/SuiteTableTree/utils/find-case.ts';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { findCaseInGroupRun } from '@Pages/Runs/entities/Details/utils';
import { Checkbox, Empty, Flex, Skeleton, Tree, Typography } from 'antd';
import entries from 'lodash/entries';
import filter from 'lodash/filter';
import get from 'lodash/get';
import includes from 'lodash/includes';
import keys from 'lodash/keys';
import map from 'lodash/map';
import reduce from 'lodash/reduce';
import size from 'lodash/size';
import { Key, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { NodeHeader } from './components';

export const SuiteTableTree = () => {
    const [selectedCaseIds, setSelectedCaseIds] = useState<Record<string, string[]>>()
    const { t } = useTranslation()
    const runItem = useGroupedRunStore((state) => state.runItem)
    const isLoading = useGroupedRunStore((state) => state.isLoading)
    const setSelectedCase = useGroupedRunStore((state) => state.setSelectedCase)
    const setCurrentCaseSuite = useGroupedRunStore((state) => state.setCurrentCaseSuite)
    const setOpenedCaseId = useGroupedRunStore((state) => state.setOpenedCaseId)
    const openedCaseId = useGroupedRunStore((state) => state.openedCaseId)
    const flatSuites = useGroupedRunStore((state) => state.flatSuites)
    const selectedCases = useGroupedRunStore((state) => state.selectedCases)
    const setDrawerOpen = useGroupedRunStore((state) => state.setDrawerOpen)
    const setActiveKey = useTestCaseStore((state) => state.setActiveDrawerKey)
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)
    const [searchParams, updateSearchParams] = useSearchParams()
    const isSearchMounted = useRef(false)

    const suiteKeys = useMemo(() => keys(flatSuites), [flatSuites])

    const renderTable = useCallback(({ node, selectedCases }: {
        node: any,
        selectedCases: ITestCase[],
    }) => {
        const suite = node as ISuiteInGroupedRun

        const items = suite.cases as unknown as ITestCase[]

        const handleSelect = (keys: ITestCase[]) => {
            setSelectedCase({
                [suite.suite_id]: keys as unknown as ITestCase[]
            })

            setSelectedCaseIds({
                [suite.suite_id]: keys.map((item) => item.case_id) || []
            })
        }

        return (
            <DefaultCaseTable
                key={ suite.suite_id }
                data={ items }
                onSelect={ handleSelect }
                props={ {
                    onRow: (props: ITestCase) => ({
                        onClick: () => {
                            const currentCase = findCaseById(runItem?.parallel, props.group_run_case_id)

                            setDrawerOpen(true)
                            setCurrentCase(currentCase)
                            setCurrentCaseSuite(suite)
                            setOpenedCaseId(props.group_run_case_id)
                        },
                        style: {
                            background: props.group_run_case_id === openedCaseId ? 'rgba(0, 0, 0, 0.02)' : undefined
                        }
                    })
                } }
                selectedKeys={ selectedCases }
            />
        )
    }, [openedCaseId])

    const suites = useMemo(() => runItem?.parallel, [runItem])

    const showTable = useCallback(({ cases }: { cases: unknown[] }): boolean => {
        return size(cases) > 0
    }, [runItem])

    const getAllCasesAndSuites = (suite: ISuiteInGroupedRun): {
        cases: Record<string, string[]>;
        suiteKeys: string[]
    } => {
        const cases = {
            [suite.suite_id]: suite.cases.map((item) => item.case_id),
        };
        const suiteKeys = [suite.suite_id];

        if (suite.children) {
            suite.children.forEach((childSuite) => {
                const childData = getAllCasesAndSuites(childSuite);

                Object.assign(cases, childData.cases);
                suiteKeys.push(...childData.suiteKeys);
            });
        }

        return { cases, suiteKeys };
    };


    const handleCheck = useCallback((_keys: string[], info: {
        checked: boolean,
        node: { data: ISuiteInGroupedRun }
    }) => {
        const suiteData: ISuiteInGroupedRun = info?.node?.data;

        const { cases: allCasesBySuiteId, suiteKeys: allSuiteKeys } = getAllCasesAndSuites(suiteData);

        if (info?.checked) {
            const updatedSelectedCases = { ...selectedCaseIds, ...allCasesBySuiteId };

            setSelectedCaseIds(updatedSelectedCases)

        } else {
            const updatedSelectedCases = { ...selectedCaseIds };

            allSuiteKeys.forEach((suiteId) => {
                updatedSelectedCases[suiteId] = [];
            });

            setSelectedCaseIds(updatedSelectedCases)
        }
    }, [selectedCases, setSelectedCase]);

    const handleSelectAll = useCallback((checked: boolean) => {
        if (!suites) return;

        const allCasesBySuiteId = reduce(entries(flatSuites), (acc, [key, value]) => {
            acc[key] = map(value, (item) => item.case_id);

            return acc;
        }, {} as Record<string, string[]>);

        const allSuiteIds = keys(allCasesBySuiteId);

        if (checked) {
            setSelectedCaseIds(allCasesBySuiteId)
        } else {
            const clearedSelectedCases = reduce(allSuiteIds, (acc, suiteId) => {
                acc[suiteId] = [];

                return acc;
            }, {} as Record<string, string[]>);

            setSelectedCaseIds(clearedSelectedCases)
        }
    }, [suites, setSelectedCase]);

    useEffect(() => {
        if (runItem?.parallel) {
            const selectedCases = reduce(keys(selectedCaseIds), (acc, key) => {
                acc[key] = filter(flatSuites[key],
                    (testCase) => includes(get(selectedCaseIds, key), testCase.case_id)
                ) || []


                return acc;
            }, {} as Record<string, ITestCase[]>)

            setSelectedCase(selectedCases)
        }
    }, [selectedCaseIds, runItem, flatSuites]);

    const [_expandedKeys, setExpandedKeys] = useState<string[]>([]);

    const handleToggleExpand = useCallback((nodeKey: string) => {
        setExpandedKeys((prev) => (includes(prev, nodeKey) ? filter(prev, (k) => k !== nodeKey) : [...prev, nodeKey]))
    }, [])

    const handleExpand = (keys: Key[]) => {
        setExpandedKeys(keys as string[])
    }

    const renderNode = (nodes: ISuiteInGroupedRun[]) => {
        return map(nodes, (node) => {
            const nodeKey = node.suite_id
            const isShowTable = showTable?.(node)
            const ComponentTable = renderTable({
                node,
                selectedCases: selectedCases?.[node.suite_id] || []
            })

            const title = (
                <NodeHeader
                    name={ node?.suite_name }
                    onClick={ handleToggleExpand.bind(null, nodeKey) }
                    { ...node }
                />
            )

            return (
                <Tree.TreeNode
                    key={ `${nodeKey}` }
                    checkable={ true }
                    // @ts-ignore
                    data={ node }
                    selectable={ false }
                    style={ { marginBottom: 0, padding: '6px 4px 0 4px' } }
                    title={ title }
                >
                    {isShowTable && (
                        <Tree.TreeNode
                            key={ `tableKey-${nodeKey}` }
                            checkable={ false }
                            className="no-indent-node table-tree-node"
                            selectable={ false }
                            title={ ComponentTable }
                            disabled
                        />
                    )}
                    {node.children?.length ? renderNode(node.children) : null}
                </Tree.TreeNode>
            )
        })
    }

    useEffect(() => {
        return () => {
            setOpenedCaseId(undefined)
        }
    }, []);

    useEffect(() => {

        if (openedCaseId) {
            setDrawerOpen(true)
            updateSearchParams((prev) => {
                prev.set(URL_QUERY_KEYS.CASE_ID, openedCaseId)

                return prev

            })
        }
    }, [openedCaseId, updateSearchParams]);

    useEffect(() => {
        const caseId = searchParams.get(URL_QUERY_KEYS.CASE_ID)
        const activeKey = searchParams.get(URL_QUERY_KEYS.DRAWER_STATE)
        const suites = runItem?.parallel

        if (caseId && suites && !isSearchMounted.current) {
            const { suites: openedSuites, currentSuite, case: openedCase } = findCaseInGroupRun(suites, caseId) || {}

            isSearchMounted.current = true
            if (currentSuite && openedCase) {
                setCurrentCase(openedCase)
                setCurrentCaseSuite(currentSuite)
                setOpenedCaseId(openedCase?.group_run_case_id)
                setDrawerOpen(true)
                if (openedSuites) {
                    setExpandedKeys((prev) => ([...prev, ...openedSuites]))
                }
                if (activeKey) {
                    setActiveKey(activeKey)
                }
            }
        }
    }, [searchParams, isSearchMounted.current, runItem]);

    useEffect(() => {
        setExpandedKeys(suiteKeys || [])
    }, [suiteKeys]);

    if (isLoading) {
        return (
            <Flex gap={ 8 } vertical>
                {Array.from({ length: 3 }).map((_item, index) => (
                    <Skeleton.Node
                        key={ `skeleton-tree-${index}` }
                        style={ { width: '100%', height: 18 } }
                    />
                ))}
            </Flex>
        )
    }

    if (!runItem) return null

    if (!size(suites)) {
        return <Empty/>
    }

    return (
        <>
            <Checkbox
                className={ 'selectable-no-transition' }
                onChange={ (e) => handleSelectAll(e.target.checked) }
                style={ { marginLeft: '4px', marginBottom: 8, width: 'fit-content' } }
            >
                <Typography.Text>{t('group_run.select_all')}</Typography.Text>
            </Checkbox>


            {/* TODO: Пофисить типизацию */}
            <Tree
                checkedKeys={ keys(selectedCases) || [] }
                // checkStrictly={ true }
                className="custom-tree-table"
                expandedKeys={ _expandedKeys }
                motion={ false }
                onCheck={ (data, info) => {
                    // @ts-ignore
                    const keys = data?.checked || []

                    // @ts-ignore
                    handleCheck(keys, info)
                } }
                onExpand={ handleExpand }
                selectable={ false }
                blockNode
                checkable
                virtual
            >
                {renderNode(suites || [])}
            </Tree>
        </>
    )
}

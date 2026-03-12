import { useThemeToken } from '@Common/hooks';
import { useProjectStore } from '@Entities/project/store';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { ISuite } from '@Entities/suite/models';
import { suiteQueries } from '@Entities/suite/queries';
import {
    type ITreeListItemWithTotal,
    treeSuiteAdapterWithTotal,
    getAllCasesAndSuites,
    collectAllCasesFromTree,
    collectAllSuiteIds
} from '@Features/runs/create-run-from-cases/components/SelectCaseForm/components/Tree/helper';
import { ICaseWithExecution, useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { useQuery } from '@tanstack/react-query';
import { Checkbox, Flex, Skeleton, Tree, TreeProps, Typography } from 'antd';
import { CheckboxChangeEvent } from 'antd/lib';
import compact from 'lodash/compact';
import entries from 'lodash/entries';
import get from 'lodash/get';
import head from 'lodash/head';
import size from 'lodash/size';
import React, { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

const TreeNode = (props: ITreeListItemWithTotal) => {
    const tempCases = useCreateRunStore((state) => state.tempCases);
    const token = useThemeToken();
    const suiteId = props?.suite.suite_id;
    const currentTestCasesSize = size(get(tempCases, suiteId, []));

    const isAll = props?.totalCaseCount === currentTestCasesSize && props?.totalCaseCount > 0;

    return (
        <Flex
            align={ 'center' }
            className={ isAll ? 'node-all-checked' : undefined }
            flex={ 1 }
            gap={ 6 }
            justify={ 'space-between' }
            style={ { width: '100%', wordBreak: 'break-all' } }
        >
            <Typography.Text>{props?.suite?.name}</Typography.Text>
            <Typography.Text style={ { whiteSpace: 'nowrap', fontSize: '12px', color: token.colorTextDescription } }>
                {props.totalSelectedCaseCount}/{props?.totalCaseCount}
            </Typography.Text>
        </Flex>
    );
};

const renderTreeNodes = (data: ITreeListItemWithTotal[], tempCases: Record<string, ICaseWithExecution[]>) => {

    
    return data.map((item) => {
        const suite = item.suite;
        const currentSuite = tempCases?.[item.suite.suite_id];

        return (
            <Tree.TreeNode
                key={ item.key }
                checked={ true }
                /*
                 * TODO: Подумать как это пофиксить, надо прокидывать data в ноду, чтобы использовать данные
                 */
                /* @ts-ignore */
                data={ suite }

                data-checked={ size(currentSuite) }
                selectable={ true }
                title={ <TreeNode { ...item } /> }
            >
                {item.children && renderTreeNodes(item?.children, tempCases)}
            </Tree.TreeNode>
        );
    });
};

export interface IProps {
    executionMode: EExecutionMode;
}

export const SuiteSelectableTree = ({ executionMode }: IProps) => {
    const { t } = useTranslation()
    const setTempSuite = useCreateRunStore((state) => state.setTempSuites);
    const selectedSuites = useCreateRunStore((state) => state.selectedSuiteId);
    const tempSuites = useCreateRunStore((state) => state.tempSuites);
    const setCurrentSuite = useCreateRunStore((state) => state.setCurrentSuite);
    const projectId = useProjectStore((state) => state.currentProject)?.project_id;
    const tempCases = useCreateRunStore((state) => state.tempCases);
    const setTempCases = useCreateRunStore((state) => state.setTempCases);

    const token = useThemeToken();

    const { isLoading, data } = useQuery(suiteQueries.userTree({ project_id: projectId }, !!projectId));

    const treeData = 
    useMemo(() => treeSuiteAdapterWithTotal(head(data)?.suites, tempCases, executionMode), 
        [data, tempCases, executionMode]);

    const handleCheck: TreeProps['onCheck'] = (_checkedKeysValue, info) => {
        /* Та же проблема с data, что и выше */
        /* @ts-ignore */
        const suiteData: ISuite = info?.node?.data;

        const { cases: allCasesBySuiteId, suiteKeys: allSuiteKeys } = getAllCasesAndSuites(suiteData, executionMode);

        if (info.checked) {
            const updatedCases = { ...tempCases };
            
            // For each suite selected, update its cases
            entries(allCasesBySuiteId).forEach(([suiteId, newTestArgs]) => {
                const existingCases = updatedCases[suiteId] || [];
                const newCaseIds = new Set(newTestArgs.map((c) => c.id));
                
                const remainingCases = existingCases.filter((c) => !newCaseIds.has(c.id));
                
                updatedCases[suiteId] = [...remainingCases, ...newTestArgs];
            });

            setTempCases(updatedCases);
            setTempSuite([...new Set([...tempSuites, ...allSuiteKeys])]);
        } else {
            const updatedTempCases = { ...tempCases };

            allSuiteKeys.forEach((suiteId) => {
                const existingCases = updatedTempCases[suiteId] || [];
                // ONLY remove cases that match the current execution mode
                const remainingCases = existingCases.filter((c) => c.executionMode !== executionMode);
                
                if (remainingCases.length > 0) {
                    updatedTempCases[suiteId] = remainingCases;
                } else {
                    /*
                     * If no cases left (or only empty array), delete the key?
                     * Or keep it empty? Original code set it to []
                     * But if we delete it, it might affect tree counts?
                     */
                    updatedTempCases[suiteId] = [];
                }
            });
            setTempCases(updatedTempCases);
            
            const updatedTempSuites = tempSuites.filter((id) => !allSuiteKeys.includes(id));

            setTempSuite(updatedTempSuites);
        }
    };

    useEffect(() => {
        setTempSuite(selectedSuites);
    }, [selectedSuites]);

    useEffect(() => {
        return () => {
            setCurrentSuite(undefined);
        };
    }, []);

    const handleSelect = (keys: React.Key[], info: unknown) => {
        /* @ts-ignore */
        const suite = info?.node?.data as ISuite | undefined;
        /* @ts-ignore */
        const selected = info?.selected as boolean;
        const key = keys?.[0] as string;

        if (!selected) {
            setCurrentSuite(undefined);
        }

        if (!key) return;

        setCurrentSuite(suite);
    };

    const checkedTotal = useMemo(
        () => {
            const keysCases = compact(entries(tempCases)?.map(([key, value]) => (size(value) ? key : null)));

            return [...tempSuites, ...keysCases];
        },
        [tempCases, tempSuites]
    );

    if (isLoading) {
        return <Skeleton/>;
    }

    const handleSelectAll = (e: CheckboxChangeEvent) => {
        if (e.target.checked) {
            const allSuiteIds = collectAllSuiteIds(treeData);
            const allCases = collectAllCasesFromTree(treeData, executionMode);

            setTempSuite(allSuiteIds);
            setTempCases(allCases);
        } else {
            const allSuiteIds = collectAllSuiteIds(treeData);
            const emptyCases: Record<string, ICaseWithExecution[]> = {};

            allSuiteIds.forEach((suiteId) => {
                emptyCases[suiteId] = [];
            });

            setTempSuite([]);
            setTempCases(emptyCases);
        }
    };

    return (
        <Flex gap={ 12 } vertical>
            <Checkbox onChange={ handleSelectAll } style={ { width: 'fit-content' } }>
                {t('common.selectAll')}
            </Checkbox>
            <Flex style={ { overflow: 'hidden', flex: 1 } }>

                <Tree
                    checkedKeys={ checkedTotal }
                    onCheck={ handleCheck }
                    onSelect={ (keys, info) => handleSelect(keys, info) }
                    style={ {
                        minWidth: '320px',
                        paddingRight: 16,
                        scrollbarWidth: 'thin',
                        width: 420,
                        height: '100%',
                        overflow: 'auto',
                        borderRight: `1px solid ${token.colorBorder}`,
                    } }
                    blockNode
                    checkable
                    checkStrictly
                    defaultExpandAll
                >
                    {renderTreeNodes(treeData, tempCases)}
                </Tree>
            </Flex>
        </Flex>
    );
};

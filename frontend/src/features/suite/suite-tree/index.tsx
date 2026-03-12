import { LoadingOutlined } from '@ant-design/icons';
import { DragOverTypes, DragTypes } from '@Common/consts';
import { IError } from '@Common/types';
import { ITreeListItem } from '@Components/TreeList/models.ts';
import { useDroppable } from '@dnd-kit/core';
import { useUpdateSuite } from '@Entities/suite/queries/mutations.ts';
import { useSuiteStore } from '@Entities/suite/store';
import { treeSuiteAdapter } from '@Entities/suite/utils';
import { findSuiteByCaseId, findSuiteWithAllParents } from '@Features/suite/suite-tree/helper.ts';
import { DropDownButton } from '@Features/suite/suite-tree/DropDownButton.tsx';
import { TreeProps, message, Spin, Tree, Flex, Typography } from 'antd';
import { AxiosError } from 'axios';
import head from 'lodash/head';
import includes from 'lodash/includes';
import isString from 'lodash/isString';
import map from 'lodash/map';
import size from 'lodash/size';
import { Key, ReactElement, useMemo, useState, ReactNode, useEffect, useCallback, isValidElement } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSuiteControl } from './hooks/useSuiteControl';

export interface IInfoSuite {
    selectedNodes: ITreeListItem[]
}

interface IProps {
    isLoading?: boolean
    record: ITreeListItem
    DropDown?: ReactNode
    isActive?: boolean
}

export const NodeTitle = ({ isLoading, isActive, record, DropDown: DropDownComponent }: IProps): ReactElement => {
    const { count, title } = record || {}
    const setHoveredSuiteId = useSuiteStore((state) => state.setHoveredSuiteId)
    const hoveredId = useSuiteStore((state) => state.hoveredSuiteId)

    const getCount = (): string => {
        if (!count) return ''

        return String(count)
    }

    const resultCount = getCount()

    const { setNodeRef, isOver } = useDroppable({
        id: record.suite.suite_id, data: {
            overType: DragOverTypes.SUITE,
            data: record
        }
    })


    if (isOver && hoveredId !== record.suite.suite_id) {
        setHoveredSuiteId(record.suite.suite_id)
    }

    return (
        <>
            <div
                ref={ setNodeRef }
                style={ { zIndex: -2, position: 'absolute', width: '100%', height: '100%', left: 0 } }
            />
            <Flex
                align="center"
                className={ isActive || isOver ? 'active-tree-node' : undefined }
                justify="space-between"
            >
                {isValidElement(title) || isString(title) ?
                    <Typography style={ { paddingRight: '2px' } }>{title}</Typography> : ''}

                {isLoading ?
                    <Spin indicator={ <LoadingOutlined spin/> } size="small"/> :

                    <Flex gap={ 8 }>
                        {resultCount && <Typography style={ { whiteSpace: 'nowrap' } }>{resultCount}</Typography>}
                        {DropDownComponent}
                    </Flex>
                }
            </Flex>
        </>
    )

}

export const SuiteTree = ({ suiteChanging }: {
    suiteChanging?: string,
}): ReactElement | undefined => {
    const setSuite = useSuiteStore((state) => state.setSuite)
    const selectedSuite = useSuiteStore((state) => state.selectedSuite)
    const [rowChanging, setRowChanging] = useState<string | null>(null)
    const { mutateAsync, isSuccess } = useUpdateSuite()
    const { data, isLoading, isSuccess: querySuccess } = useSuiteControl()
    const [gData, setGData] = useState<ITreeListItem[]>([]);
    const hoveredSuiteId = useSuiteStore((state) => state.hoveredSuiteId)
    const [expandedKeys, setExpandedKeys] = useState<string[]>([])
    const success = isSuccess || querySuccess
    const [searchParams, updateSearchParams] = useSearchParams()
    const selectedSuiteId = selectedSuite?.suite_id || ''

    // const flatData = useMemo(() => flat)
    const adaptedTreeData = useMemo(() => treeSuiteAdapter(head(data)?.suites), [data])

    const handleChange = async ({ currentId, parentId, toGap, position, node }: {
        currentId: string,
        parentId: string | null,
        toGap?: boolean,
        position?: number
        node: unknown
    }) => {
        // @ts-ignore
        const currentParentId = toGap ? node?.parent_suite?.key : parentId

        try {
            setRowChanging(parentId)
            await mutateAsync({
                suite_id: currentId,
                parent_id: currentParentId,
                new_position: position
            })

        } catch (e) {
            const axiosError = e as AxiosError<IError>
            const error = axiosError?.response?.data.detail || 'Something went wrong...'

            message.error(error)
        } finally {
            setRowChanging(null)
        }
    }

    const handleOnSelect = (_data: Key[], info?: IInfoSuite) => {
        // const suiteId = (data && size(data)) ? String(head(data)) : null
        if (info && size(info?.selectedNodes)) {
            const selectedSuite = info?.selectedNodes[0]?.suite

            setSuite(selectedSuite)
            updateSearchParams({
                suiteId: selectedSuite?.suite_id
            })
        } else {
            setSuite(null)
            searchParams.delete('suiteId')
            updateSearchParams()
        }
    }

    const onDrop: TreeProps['onDrop'] = (info) => {
        handleChange({
            currentId: info.dragNode.key.toString(),
            position: info.dropPosition,
            toGap: info.dropToGap,
            parentId: info.dropPosition < 0 ? null : info.node.key.toString(),
            node: info.node
        })
    };

    useEffect(() => {
        const suiteId = searchParams.get('suiteId')
        const caseId = searchParams.get('caseId')
        const suites = head(data)?.suites

        if (suites && caseId && !suiteId) {
            const suite = findSuiteByCaseId(suites, caseId)


            if (suite) {
                updateSearchParams((prev) => {
                    prev.set('suiteId', suite?.suite_id)

                    return prev
                })
            }
        }

        if (!selectedSuite && suiteId && suites) {
            const { suite, parentIds } = findSuiteWithAllParents(suites, suiteId)

            if (suite) {
                setTimeout(() => {
                    setExpandedKeys(parentIds)
                    setSuite(suite)
                }, 100)
            }
        }
    }, [searchParams, data]);

    useEffect(() => {
        if (success) {
            setGData(adaptedTreeData)
        }
    }, [adaptedTreeData, success]);


    useEffect(() => {
        if (hoveredSuiteId) {
            if (!includes(expandedKeys, hoveredSuiteId)) {

                setExpandedKeys((prev) => Array.from(new Set([...prev, hoveredSuiteId])))
            }
        }
    }, [hoveredSuiteId]);

    useEffect(() => {
        setRowChanging(suiteChanging || null)
    }, [suiteChanging]);

    const renderNode = useCallback((nodes: ITreeListItem[]) => {
        return map(nodes, (node) => {

            return (

                <Tree.TreeNode
                    data-active={ node?.key === hoveredSuiteId }
                    data-droppable={ true }
                    data-has-child={ size(node.children) > 0 }
                    data-id={ node.key }
                    eventKey={ DragTypes.DRAGGABLE_CASE }
                    title={ <NodeTitle
                        DropDown={ <DropDownButton record={ node }/> }
                        isLoading={ rowChanging === node.key }
                        record={ node }
                    /> }
                    selectable
                    { ...node }
                    key={ node.key }
                >
                    {node.children && renderNode(node.children as unknown as ITreeListItem[])}
                </Tree.TreeNode>

            )
        })
    }, [])


    if (isLoading) {
        return <Spin/>
    }
    if (!adaptedTreeData) {

        return undefined
    }


    return (
        <Tree
            className={ `draggable-tree full-selected-node-tree` }
            draggable={ true }
            expandedKeys={ expandedKeys }
            onDrop={ onDrop }
            onExpand={ (expanded) => setExpandedKeys(expanded as []) }
            onSelect={ handleOnSelect }
            selectable={ true }
            selectedKeys={ [selectedSuiteId] }
            titleRender={ (props) => (
                <NodeTitle
                    DropDown={ <DropDownButton record={ props }/> }
                    isLoading={ rowChanging === props.key }
                    record={ props }
                />
            ) }
            treeData={ gData }
            blockNode
        />
    )
}


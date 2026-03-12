import { Tree } from 'antd';
import keys from 'lodash/keys';
import React, { useState, ReactNode, Key, useCallback, useEffect, memo, useMemo } from 'react';

export interface ITreeNode<T> {
    children?: ITreeNode<T>[];

    [key: string]: any;
}

export interface ITableProps<T> {
    node: ITreeNode<T>;
    selectedKeys?: Set<string>;
    onSelect?: (id: string, checked: boolean) => void;
}

interface ITableTreeProps<T> {
    nodes: ITreeNode<T>[];
    tableComponent?: React.ComponentType<ITableProps<T>>;
    /* Рендер хэдера ноды */
    renderNodeHeader?: (node: ITreeNode<T>, onClick: () => void) => ReactNode;
    /* Ключ для каждой ноды (ключ именно в объекте ноды) */
    keyIndex: string
    nodeKeySeparator?: string;
    /* Функция, которая возвращает значение, надо ли показывать таблицу в конкретной ноде */
    showTable?: (node: ITreeNode<T>) => void
    onSelect?: (selectedNodes: Key[], info?: unknown) => void

    selectedNodes?: Record<string, string[]>
}

export const TableTree = memo(
    <T extends object>(
        {
            nodes,
            tableComponent: Table,
            renderNodeHeader,
            selectedNodes,
            showTable,
            onSelect,
            keyIndex,
        }:
            ITableTreeProps<T>,
    ) => {
        //@ts-ignore
        const [_expandedKeys, setExpandedKeys] = useState<string[]>([]);
        // const [selectedKeys] = useState<Set<string>>(new Set());

        const handleExpand = (keys: Key[]) => {
            setExpandedKeys(keys as string[])
        }

        const buildTreeNodes = useCallback(
            (nodes: ITreeNode<T>[]): React.ReactNode[] =>
                nodes.map((node) => {
                    const nodeKey = `${node[keyIndex]}`;
                    const isShowTable = showTable?.(node) ?? true;

                    const TableComponent = Table ? <Table key={ `table-${nodeKey}` } node={ node }/> : null

                    const headerAction = renderNodeHeader?.(node, () =>
                        setExpandedKeys((prev) =>
                            (prev.includes(nodeKey)
                                ? prev.filter((k) => k !== nodeKey)
                                : [...prev, nodeKey])
                        )
                    );


                    return (
                        <Tree.TreeNode
                            key={ `${nodeKey}` }
                            checkable={ isShowTable }
                            //@ts-ignore
                            data={ node }
                            selectable={ false }
                            style={ { marginBottom: 0, padding: '6px 4px 0 4px' } }
                            title={ headerAction || <div>node</div> }
                        >
                            {isShowTable && (
                                <Tree.TreeNode
                                    key={ `tableKey-${nodeKey}` }
                                    checkable={ false }
                                    className="no-indent-node table-tree-node"
                                    selectable={ false }
                                    title={ TableComponent }
                                    disabled
                                />
                            )}
                            {node.children?.length ? buildTreeNodes(node.children) : null}
                        </Tree.TreeNode>
                    );
                }),
            [Table, keyIndex, showTable, renderNodeHeader]
        );


        const getAllNodeKeys = useCallback((nodes: ITreeNode<T>[]): string[] => {
            return nodes.reduce((acc, node) => {
                const nodeKey = `${node[keyIndex]}`;

                acc.push(nodeKey);
                if (node.children) {
                    //@ts-ignore
                    acc.push(...getAllNodeKeys(node.children, nodeKey));
                }

                return acc;
            }, [] as string[]);
        }, [nodes]);


        useEffect(() => {
            const allKeys = getAllNodeKeys(nodes);

            setExpandedKeys((prev) =>
                (prev.length === allKeys.length && prev.every((k) => allKeys.includes(k))
                    ? prev
                    : allKeys)
            );
        }, [nodes, getAllNodeKeys]);

        const keysSelectedNodes = useMemo(
            () => (selectedNodes ? keys(selectedNodes) : []),
            [selectedNodes]
        );

        return (
            <Tree
                checkedKeys={ keysSelectedNodes }
                checkStrictly={ true }
                className="custom-tree-table"
                expandedKeys={ _expandedKeys }
                //@ts-ignore
                onCheck={ (data, info) => {
                    //@ts-ignore
                    const keys = data?.checked || []

                    onSelect?.(keys, info)
                } }
                onExpand={ handleExpand }
                selectable={ false }
                blockNode
                checkable
                virtual
            >
                {buildTreeNodes(nodes)}
            </Tree>
        );
    }
);


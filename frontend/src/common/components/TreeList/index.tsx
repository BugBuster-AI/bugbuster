import { TreeNode } from '@Components/TreeList/components/TreeNode.tsx';
import { ITreeListItem } from '@Components/TreeList/models.ts';
import { Tree } from 'antd';
import type { TreeProps } from 'antd';
import includes from 'lodash/includes';
import { Key, ReactElement, ReactNode, useEffect, useState } from 'react';

export interface IInfoSuite {
    selectedNodes: ITreeListItem[]
}

export const findSelectedNodes = (treeData: ITreeListItem[], selectedKeys: Key[]): ITreeListItem[] => {
    const selectedNodes: ITreeListItem[] = [];

    const traverse = (nodes: ITreeListItem[]) => {
        nodes.forEach((node) => {
            if (includes(selectedKeys, node.key)) {
                selectedNodes.push(node);
            }
            if (node.children) {
                //@ts-ignore
                traverse(node.children);
            }
        });
    };

    traverse(treeData);

    return selectedNodes;
};

interface IProps {
    treeData?: ITreeListItem[]
    onDropHandler?: ({ currentId, parentId, position, toGap }: {
        currentId: string,
        parentId: string | null,
        position?: number,
        toGap?: boolean
        node: unknown
    }) => void
    onDragEnter?: () => void
    rowLoading?: string | null
    isError?: boolean
    onSelect?: (keys: Key[], info?: IInfoSuite) => void
    isLoading?: boolean
    isSuccess?: boolean
    defaultSelectedKeys?: Key[]
    selectedKeys?: Key[]
    DropDownComponent?: ({ record }: { record: ITreeListItem }) => ReactNode
    className?: string
    treeProps?: TreeProps<ITreeListItem>
}

export const TreeList = (
    {
        treeData,
        isSuccess,
        rowLoading,
        onSelect,
        onDropHandler,
        selectedKeys,
        defaultSelectedKeys,
        DropDownComponent,
        className,
        treeProps
    }:
        IProps): ReactElement | null => {
    const [gData, setGData] = useState(treeData);

    const onDrop: TreeProps['onDrop'] = (info) => {
        if (onDropHandler) {
            onDropHandler({
                currentId: info.dragNode.key.toString(),
                position: info.dropPosition,
                toGap: info.dropToGap,
                parentId: info.dropPosition < 0 ? null : info.node.key.toString(),
                node: info.node
            })
        }


        return
    };

    const onDragStart: TreeProps['onDragStart'] = () => {
        /*
         * Сохраняем резервную копию данных перед началом перемещения
         * setBackupData([...gData]);
         */
    };

    useEffect(() => {
        if (isSuccess) {
            setGData(treeData)
        }
    }, [treeData, isSuccess]);
    

    if (!treeData) return null

    return (
        <Tree
            className={ `draggable-tree ${className || ''}` }
            defaultExpandedKeys={ defaultSelectedKeys }
            defaultSelectedKeys={ defaultSelectedKeys }
            onDragStart={ onDragStart }
            onDrop={ onDrop }
            onSelect={ onSelect }
            selectable={ true }
            selectedKeys={ selectedKeys }
            titleRender={ (props) => (
                <TreeNode
                    DropDown={ DropDownComponent?.({ record: props }) || undefined }
                    isLoading={ rowLoading === props.key }
                    record={ props }
                />
            ) }
            treeData={ gData }
            blockNode
            draggable
            { ...treeProps }
        />
    );
};


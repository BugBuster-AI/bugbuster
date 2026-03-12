import { HolderOutlined } from '@ant-design/icons';
import { IDraggableItemOperationData } from '@Components/DraggableList/models.ts';
import { CollisionPriority } from '@dnd-kit/abstract';
import { useDroppable } from '@dnd-kit/react'
import { useSortable } from '@dnd-kit/react/sortable'
import { Button, Flex, FlexProps, Form, FormListFieldData, FormListOperation } from 'antd';
import { CSSProperties, ReactElement, ReactNode, useRef } from 'react';

interface IProps {
    name: string | (string | number)[];
    accept?: string | string[];
    type?: string
    dataType?: string
    enableDropTarget?: boolean
    style?: CSSProperties
    children: (fields: FormListFieldData[], handlers: FormListOperation, parentElement?: HTMLDivElement | null) =>
        ReactNode;
}

const DraggableList = ({ children, enableDropTarget = true, name, dataType, type, accept, style }: IProps) => {
    const parentElement = useRef<HTMLDivElement>(null)
    const { ref, isDropTarget } = useDroppable({
        id: typeof name === 'string' ? name : name.join('-'),
        disabled: !enableDropTarget,
        data: {
            id: name,
            name,
            type: dataType || 'column',
        } as IDraggableItemOperationData,
        type: type || 'column',
        accept: accept || 'item',
        register: true,
        collisionPriority: CollisionPriority.Normal
    });

    const isDropping = enableDropTarget ? isDropTarget : false;

    return (
        <div
            ref={ ref }
            style={ {
                padding: 4,
                transition: '.2s ease',
                background: isDropping ? '#e7f4ff' : 'transparent',
                borderRadius: 12,
                ...style
            } }>
            <div ref={ parentElement }>
                <Form.List name={ name }>
                    {(fields, { add, move, remove }) => {
                        return children(fields, { add, move, remove }, parentElement.current)
                    }}
                </Form.List>
            </div>
        </div>
    );
};

interface IItemProps {
    id: number | string;
    parentElement?: HTMLDivElement | Element | null
    index: number;
    children: ReactElement;
    props?: FlexProps;
    group?: string
    isDrag?: boolean;
    itemData?: Record<string, string>

    accept?: string | string[]
    type?: string
    style?: CSSProperties
    domId?: string
    dataType?: string
}

DraggableList.Item = ({
    id,
    children,
    accept,
    type,
    dataType,
    props,
    index,
    group,
    style: overrideStyle,
    parentElement,
    isDrag = true,
    domId,
    ...itemData
}: IItemProps) => {
    const { ref, handleRef } = useSortable({
        type: type || 'item',
        accept: accept || 'item',
        data: {
            id,
            index,
            group,
            type: dataType || 'item',
            ...itemData
        } as IDraggableItemOperationData,
        group,
        id,
        index
    });


    const style: React.CSSProperties = {
        /*
         * transform: CSS.Transform.toString(transform),
         * transition: transition || undefined,
         */
        opacity: 1,
        cursor: 'default',
        ...overrideStyle
    };

    return (
        <div
            ref={ ref }
            data-dragging={ false }
            id={ domId }
            style={ style }>
            <Flex
                align="flex-start"
                className="no-errors-margin"
                gap={ 8 }
                { ...props }
                style={ { ...props?.style, width: '100%', cursor: 'default!important' } }
            >
                {isDrag && (
                    <Button
                        ref={ handleRef }
                        className={ 'grab-button' }
                        icon={ <HolderOutlined/> }
                        style={ { minWidth: 32 } }
                        type="text"
                    />
                )}
                {children}
            </Flex>
        </div>
    );
};

export { DraggableList };

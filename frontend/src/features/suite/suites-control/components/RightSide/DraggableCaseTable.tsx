import { HolderOutlined } from '@ant-design/icons';
import { COMMON_SEARCH_PARAMS, DragCaseEvents, DragOverTypes } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { asyncHandler } from '@Common/utils';
import {
    type UniqueIdentifier, DragOverlay, useDndContext, DragEndEvent
} from '@dnd-kit/core';
import { restrictToWindowEdges } from '@dnd-kit/modifiers';
import {
    SortableContext,
    useSortable,
    arrayMove
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useSuiteStore } from '@Entities/suite/store';
import { TestTypeIcon } from '@Entities/test-case/components/Icons';
import { ETestCaseType, ITestCaseListItem } from '@Entities/test-case/models';
import { useUpdateTestCase } from '@Entities/test-case/queries';
import { useSuitesControlContext } from '@Features/suite/suites-control/context';
import { Empty, Flex, Table, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableProps } from 'antd/lib';
import filter from 'lodash/filter';
import isArray from 'lodash/isArray';
import size from 'lodash/size';
import React, {
    cloneElement, Component, ComponentProps,

    CSSProperties, PropsWithChildren,
    ReactElement,
    ReactNode,
    useEffect,
    useRef,
    useState
} from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

interface IDraggableRowProps {
    id: UniqueIdentifier;
    children: ReactNode;
    record: ITestCaseListItem;
    isInsideSortContainer: boolean
    isLoading?: boolean
    onClick?: () => void
    style?: CSSProperties
}

/** Строка таблицы */
const DraggableRow = ({
    id,
    children,
    isLoading,
    record,
    onClick,
    isInsideSortContainer,
    style: propsStyle,
    ...props
}: IDraggableRowProps) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        isDragging,
        active,
        transition,
    } = useSortable({ id, data: record, disabled: !isInsideSortContainer });
    const token = useThemeToken()

    const isActiveElementOutside = !isInsideSortContainer && active?.id === id

    const style: CSSProperties = {
        transform: !isInsideSortContainer ? 'none' : CSS.Transform.toString(transform),
        opacity: (isActiveElementOutside || isLoading) ? 0 : isDragging ? 0.2 : 1,
        transition,
        zIndex: 999,
        background: isDragging ? token.colorTextPlaceholder : '',
        position: (isActiveElementOutside || isLoading) ? 'fixed' : 'relative',
        ...propsStyle
    };

    return (
        <tr
            ref={ setNodeRef }
            className={ 'ant-table-row ant-table-row-level-0 clickable-row' }
            onClick={ onClick }
            style={ style }
            { ...props }
        >
            {React.Children.map(children, (child) => {
                if (React.isValidElement(child)) {
                    if (child.key === 'sort') {
                        return <td
                            style={ { cursor: isDragging ? 'grabbing' : 'grab' } }
                            { ...attributes }
                            { ...listeners }
                        >
                            <HolderOutlined style={ { width: '100%', justifyContent: 'center' } }/>
                        </td>

                    }

                    return cloneElement(child, {
                        ...child.props,
                    });
                }

                return child;
            })}
        </tr>
    );
};

/** Оверлей, отображается, когда мы цепляем строку */
const OverlayRow = ({ isInsideSortContainer }: { isInsideSortContainer: boolean }) => {
    const { active, over } = useDndContext()

    const record = active?.data.current as ITestCaseListItem

    if (!record) return null

    return <Flex
        gap={ 16 }
        style={ {
            userSelect: 'none',
            padding: 4,
            zIndex: 99999,
            cursor: !isInsideSortContainer && over !== null ? 'copy' : 'grabbing',
            width: 'fit-content',
            position: 'fixed',
            opacity: 0.5
        } }>
        <Typography.Text style={ { width: 120 } } ellipsis>{record.case_id}</Typography.Text>
        <Typography.Text>{record.name}</Typography.Text>

    </Flex>
}

/** Сервис, который ловит ивенты драг-н-дропа */
const SortingManager = ({ onDragEnd }: { onDragEnd: (activeId: Number, overId: Number, caseId: string) => void }) => {

    const handleEnd = (e: Event) => {
        const event = e as CustomEvent<DragEndEvent>

        const active = event.detail?.active
        const over = event.detail?.over

        const activeData = active?.data?.current
        const overData = over?.data?.current

        if (active && over && activeData && overData?.overType !== DragOverTypes.SUITE) {
            onDragEnd(active.id as number, over?.id as number, activeData?.case_id)
        }
    }

    useEffect(() => {
        window.addEventListener(DragCaseEvents.DRAG_END, handleEnd)

        return () => {
            window.removeEventListener(DragCaseEvents.DRAG_END, handleEnd)
        }
    }, []);

    return null
}

interface IProps {
    data?: ITestCaseListItem[];
    renderTypeButton?: (record: ITestCaseListItem) => ReactNode;
    isLoading?: boolean;
    selectedKey?: string | null;
    onSelect?: (keys: string[]) => void;
    props?: TableProps;
    selectedKeys?: string[];
    onDragEnd?: (index: number, caseId: string) => Promise<void>;
    loadingRow?: string
    savePaginationQueryParameters?: boolean
}

export const DraggableCaseTable = ({
    loadingRow,
    data,
    isLoading,
    savePaginationQueryParameters,
    selectedKey,
    onSelect,
    props,
    selectedKeys,
}: IProps): ReactElement => {
    const { t } = useTranslation();
    const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>(selectedKeys as React.Key[] || []);
    const [dataSource, setDataSource] = useState<ITestCaseListItem[]>(data || []);
    const token = useThemeToken()
    const selectedSuite = useSuiteStore((state) => state.selectedSuite)
    const asyncUpdateCase = useUpdateTestCase()
    const [isOutsideTable, setIsOutsideTable] = useState(false);
    const tableRef = useRef<HTMLDivElement>(null);
    const { movingCaseToSuite } = useSuitesControlContext()
    const [searchParams, updateSearchParams] = useSearchParams()
    const [currentPage, setCurrentPage] = useState(1)

    const onSelectChange = (newSelectedRowKeys: React.Key[]): void => {
        onSelect && onSelect(newSelectedRowKeys as string[]);
        setSelectedRowKeys(newSelectedRowKeys);
    };

    const rowSelection = {
        selectedRowKeys,
        onChange: onSelectChange,
    };

    const columns: ColumnsType = [
        {
            width: 44,
            minWidth: 44,
            dataIndex: 'sort',
            key: 'sort',
        },
        Table.SELECTION_COLUMN,
        {
            title: t('table.type'),
            key: 'type',
            width: 68,
            align: 'center',
            dataIndex: 'type',
            render: (value) => <TestTypeIcon type={ value as ETestCaseType }/>
        },
        {
            title: t('table.id'),
            key: 'case_id',
            width: 80,
            ellipsis: true,
            align: 'center',
            dataIndex: 'case_id',
        },
        {
            title: t('table.name'),
            key: 'name',
            dataIndex: 'name',
        }
    ];

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!tableRef.current) return;

        const rect = tableRef.current.getBoundingClientRect();

        const isInside =
            e.clientX >= rect.left &&
            e.clientX <= rect.right &&
            e.clientY >= rect.top &&
            e.clientY <= rect.bottom;

        setIsOutsideTable(isInside)
    };


    const handleDragEnd = async (activeId: Number, overId: Number, caseId: string) => {

        let backupData = dataSource

        if (activeId !== overId && overId) {
            setDataSource((prev) => {
                const oldIndex = prev.findIndex((item) => item.position === activeId);
                const newIndex = prev.findIndex((item) => item.position === overId);

                return arrayMove(prev, oldIndex, newIndex);
            });

            await asyncHandler(asyncUpdateCase.mutateAsync.bind(null, {
                new_position: Number(overId),
                case_id: caseId
            }), {
                /** Восстановление предыдущих данных, в случае ошибки*/
                onError: () => setDataSource(backupData)
            })

        }
    };

    const page = searchParams.get('page')

    useEffect(() => {
        setCurrentPage(Number(page || 1))
    }, [page]);

    const defaultPaginationPage = searchParams.get('page') ? Number(searchParams.get('page') || 1) : undefined

    useEffect(() => {
        setDataSource(data || []);
    }, [data]);

    useEffect(() => {
        setSelectedRowKeys(selectedKeys || []);
    }, [selectedKeys]);

    useEffect(() => {
        if (movingCaseToSuite?.case_id) {
            setDataSource((prev) => filter(prev, (item) => item.case_id !== movingCaseToSuite.case_id))
        }
    }, [movingCaseToSuite]);

    return (
        <div
            ref={ tableRef }
            onMouseMove={ handleMouseMove }
            style={ { position: 'relative' } }
        >
            <DragOverlay modifiers={ [restrictToWindowEdges] }>
                <OverlayRow isInsideSortContainer={ isOutsideTable }/>
            </DragOverlay>

            <SortingManager onDragEnd={ handleDragEnd }/>

            <Table
                columns={ columns }
                components={ {
                    body: {
                        //@ts-ignore
                        wrapper: (props: ComponentProps<typeof Component<PropsWithChildren>>) => {
                            return (
                                <SortableContext items={ dataSource.map((item) => item.position) }>
                                    <tbody>{props.children}</tbody>
                                </SortableContext>
                            )
                        },
                        row: (rowProps: ComponentProps<typeof Component<any>>) => {
                            const { index, ...restProps } = rowProps || {};

                            if (selectedSuite && size(dataSource) === 0) {
                                return (
                                    <td colSpan={ size(columns) }>
                                        <Empty/>
                                    </td>
                                )
                            }

                            if (rowProps.className === 'ant-table-placeholder') {
                                return <tr
                                    className="ant-table-placeholder"
                                    style={ { textAlign: 'center', color: token.colorTextPlaceholder } }>
                                    {rowProps.children}
                                </tr>
                            }

                            if (!isArray(rowProps.children)) {
                                return rowProps.children
                            }


                            return (
                                <DraggableRow
                                    id={ restProps.itemKey as string }
                                    isInsideSortContainer={ isOutsideTable }
                                    isLoading={ loadingRow === rowProps?.record?.case_id }
                                    onClick={ rowProps?.onClick }
                                    record={ restProps.record }
                                    style={ restProps?.style }
                                >
                                    {restProps.children}
                                </DraggableRow>
                            );
                        },

                    },
                } }
                dataSource={ dataSource }
                loading={ isLoading }
                locale={ {
                    emptyText: selectedKey ? 'No data' : 'No data selected'
                } }
                pagination={ {
                    showTotal: () => null,
                    current: currentPage,
                    pageSize: 10,
                    defaultCurrent: (defaultPaginationPage && isNaN(defaultPaginationPage))
                        ? undefined
                        : defaultPaginationPage,
                    onChange: (page) => {
                        setCurrentPage(page);
                        if (savePaginationQueryParameters) {
                            updateSearchParams((prev) => {
                                prev.set(COMMON_SEARCH_PARAMS.PAGE, String(page))

                                return prev
                            })
                        }
                    }
                } }
                rowClassName="clickable-row"
                rowKey="case_id"
                rowSelection={ rowSelection }
                size="small"
                { ...props }
            />
        </div>
    );
};

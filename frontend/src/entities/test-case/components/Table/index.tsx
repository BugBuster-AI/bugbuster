import { DragSortTable, DragTableProps, ProColumns } from '@ant-design/pro-components';
import { TestTypeIcon } from '@Entities/test-case/components/Icons';
import { ETestCaseType, ITestCaseListItem } from '@Entities/test-case/models';
import { Table } from 'antd';
import { TableRowSelection } from 'antd/es/table/interface';
import nth from 'lodash/nth';
import { ReactElement, ReactNode, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    data?: ITestCaseListItem[]
    renderTypeButton?: (record: ITestCaseListItem) => ReactNode;
    isLoading?: boolean

    // Выбранный сьют (TODO: нужен рефакторинг)
    selectedKey?: string | null
    onSelect?: (keys: string[]) => void
    props?: DragTableProps<any, any>
    draggable?: boolean

    // Выбранные строки таблицы
    selectedKeys?: string[]
    onDragEnd?: (index: number, caseId: string) => Promise<void>
}

export const CaseTable =
    ({
        draggable = true,
        data,
        isLoading,
        selectedKey,
        onSelect,
        props,
        selectedKeys,
        onDragEnd
    }: IProps): ReactElement => {
        const { t } = useTranslation();
        const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>(selectedKeys as React.Key[] || []);
        const [dataSource, setDataSource] = useState<ITestCaseListItem[]>(data || []);

        const onSelectChange = (newSelectedRowKeys: React.Key[]): void => {
            onSelect && onSelect(newSelectedRowKeys as string[])
            setSelectedRowKeys(newSelectedRowKeys);
        };

        const handleDragSortEnd = async (
            _beforeIndex: number,
            afterIndex: number,
            newDataSource: ITestCaseListItem[],
        ): Promise<void> => {
            const draggedElement = nth(newDataSource, afterIndex)
            const prevDataSource = dataSource || [];

            setDataSource(newDataSource);

            if (draggedElement && onDragEnd) {
                try {
                    await onDragEnd(afterIndex, draggedElement.case_id as string)
                } catch {
                    setDataSource(prevDataSource);
                }
            }
        };

        const rowSelection: TableRowSelection<ITestCaseListItem> = {
            selectedRowKeys,
            onChange: onSelectChange,
        };

        const columns: ProColumns[] = [
            {
                width: 44,
                minWidth: 44,
                dataIndex: 'sort',
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

        useEffect(() => {
            setDataSource(data || []);
        }, [data]);

        useEffect(() => {
            setSelectedRowKeys(selectedKeys || [])
        }, [selectedKeys])

        return (
            <DragSortTable
                columns={ draggable ? columns : columns.slice(1) }
                dataSource={ dataSource }
                dragSortKey={ draggable ? 'sort' : undefined }
                loading={ isLoading }
                locale={ {
                    emptyText: selectedKey ? 'No data' : 'No data selected'
                } }
                onDragSortEnd={ draggable ? handleDragSortEnd : undefined }
                pagination={ {
                    showTotal: () => null,
                    pageSize: 10
                } }
                rowClassName="clickable-row"
                rowKey="case_id"
                rowSelection={ rowSelection }
                search={ false }
                size={ 'small' }
                tableAlertRender={ false }
                toolBarRender={ false }
                { ...props }
            />
        );
    };

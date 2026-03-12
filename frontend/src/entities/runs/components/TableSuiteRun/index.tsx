import { DragSortTable, DragTableProps, ProColumns } from '@ant-design/pro-components';
import { StatusBadge, TextWithIcon } from '@Common/components';
import { ERunStatus } from '@Entities/runs/models';
import { TestPriorityIcon, TestTypeIcon } from '@Entities/test-case/components/Icons';
import { ETestCaseType, ITestCase } from '@Entities/test-case/models';
import { Flex, Table } from 'antd';
import { TableRowSelection } from 'antd/es/table/interface';
import { ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IData {
    case_id: string;
    status: ERunStatus,
    name: string;
    actual_complete_time: string
    type?: string
}

export type { IData as ITableSuiteRunData }

interface IProps {
    data?: ITestCase[]
    isLoading?: boolean
    DropDownButton?: (data: ITestCase) => ReactNode
    draggable?: boolean
    isSelected?: boolean
    onSelect?: (items: ITestCase[]) => void,
    selectedKeys?: ITestCase[]
    props?: DragTableProps<any, any>
}

export const TableSuiteRun = ({
    isLoading,
    DropDownButton,
    draggable = true,
    data = [],
    onSelect,
    selectedKeys,
    isSelected,
    props
}: IProps) => {
    const [selectedRowKeys, setSelectedRowKeys] = useState<ITestCase[]>(selectedKeys || []);
    const [dataSource, setDataSource] = useState<ITestCase[]>(data || []);

    const { t } = useTranslation()

    const onSelectChange = (newSelectedRowKeys: ITestCase[]): void => {
        onSelect && onSelect(newSelectedRowKeys)
        setSelectedRowKeys(newSelectedRowKeys);
    };

    const handleDragSortEnd = (
        _beforeIndex: number,
        _afterIndex: number,
        newDataSource: ITestCase[],
    ): void => {
        setDataSource(newDataSource);
    };

    const rowSelection: TableRowSelection<ITestCase> = {
        selectedRowKeys: selectedRowKeys.map((item) => item.case_id),
        onChange: (_props, rowData) => onSelectChange(rowData),
    };

    const columns: ProColumns[] = [
        Table.SELECTION_COLUMN,
        {
            title: null,
            key: 'type',
            width: 68,
            align: 'center',
            dataIndex: 'type',
            render: (value, record) =>
                <Flex align={ 'center' } gap={ 8 } justify={ 'space-around' }>
                    <TestPriorityIcon priority={ record.priority }/>
                    <TestTypeIcon type={ value as ETestCaseType }/>
                </Flex>
        },
        {
            title: t('table.id'),
            key: 'case_id',
            width: 42,
            dataIndex: 'case_id',
            ellipsis: true,
            minWidth: 42,
        },
        {
            title: t('table.status'),
            width: 108,
            key: 'actual_status',
            dataIndex: 'actual_status',
            minWidth: 108,
            render: (value) => <StatusBadge status={ value as ERunStatus }/>
        },
        {
            title: t('table.name'),
            key: 'name',
            dataIndex: 'name'
        },
        {
            title: t('table.duration'),
            width: 144,
            key: 'duration',
            align: 'center',
            dataIndex: 'actual_complete_time',
            render: (value) => (!isNaN(Number(value))
                ? <TextWithIcon wrapperProps={ { justify: 'center' } }>
                    {Number(value).toFixed(2)} {t('common.sec')}
                </TextWithIcon>
                : '-')

        },

        {
            width: 24,
            dataIndex: 'dropdown',
            minWidth: 24,
            render: (_value, record) => (DropDownButton ? <DropDownButton { ...record }/> : '')
        }
    ];


    return (
        <DragSortTable
            columns={ draggable ? columns : columns?.slice(1) }
            dataSource={ dataSource }
            dragSortKey={ draggable ? 'sort' : undefined }
            loading={ isLoading }

            locale={ {
                emptyText: isSelected ? t('common.default_empty') : t('common.not_selected')
            } }
            onDragSortEnd={ draggable ? handleDragSortEnd : undefined }
            /*
             * pagination={ {
             *     showTotal: () => null,
             *     pageSize: 10
             * } }
             */
            pagination={ false }
            rowClassName="clickable-row"
            //@ts-ignore
            rowKey="case_id"

            rowSelection={ rowSelection }
            search={ false }
            size={ 'small' }
            tableAlertRender={ false }
            toolBarRender={ false }

            { ...props }
        />
    );
}

import { StatusBadge, TextWithIcon } from '@Common/components';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ERunStatus } from '@Entities/runs/models';
import { TestPriorityIcon, TestTypeIcon } from '@Entities/test-case/components/Icons';
import { ETestCasePriority, ETestCaseType, ITestCase } from '@Entities/test-case/models';
import { Flex, Table } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableRowSelection } from 'antd/es/table/interface';
import { TableProps } from 'antd/lib';
import { memo, ReactNode, useEffect, useState } from 'react';
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
    props?: TableProps<ITestCase>
}

export const DefaultCaseTable = memo(({
    isLoading,
    DropDownButton,
    data = [],
    onSelect,
    selectedKeys,
    isSelected,
    props
}: IProps) => {
    const [selectedRowKeys, setSelectedRowKeys] = useState<ITestCase[]>(selectedKeys || []);

    const { t } = useTranslation()

    const onSelectChange = (newSelectedRowKeys: ITestCase[]): void => {
        onSelect && onSelect(newSelectedRowKeys)
        setSelectedRowKeys(newSelectedRowKeys);
    };

    const rowSelection: TableRowSelection<ITestCase> = {
        selectedRowKeys: selectedRowKeys.map((item) => item.case_id),
        onChange: (_props, rowData) => onSelectChange(rowData),
        columnWidth: 40,

    };

    useEffect(() => {
        setSelectedRowKeys(selectedKeys || [])
    }, [selectedKeys]);

    const columns: ColumnsType<ITestCase> = [
        {
            title: null,
            key: 'type',
            width: 68,
            align: 'center',
            dataIndex: 'type',
            render: (value, record) =>
                <Flex align={ 'center' } gap={ 8 } justify={ 'space-around' }>
                    <TestPriorityIcon priority={ record.priority as ETestCasePriority }/>
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
            width: 138,
            key: 'actual_status',
            dataIndex: 'actual_status',
            minWidth: 108,
            render: (value) => <StatusBadge status={ value as ERunStatus }/>
        },
        {
            title: t('table.name'),
            width: 'auto',
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
                    {formatSeconds(Number(value || 0), t)}
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
        <Table
            className={ 'selectable-no-transition' }
            columns={ columns }
            dataSource={ data }
            loading={ isLoading }
            locale={ {
                emptyText: isSelected ? t('common.default_empty') : t('common.not_selected')
            } }
            pagination={ false }
            rowClassName="clickable-row"
            rowKey="case_id"
            rowSelection={ rowSelection }
            scroll={ {
                y: 350,
            } }
            size={ 'small' }
            virtual={ true }

            { ...props }
        />
    );
})

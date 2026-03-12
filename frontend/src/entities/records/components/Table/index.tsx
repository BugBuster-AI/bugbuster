import { IRecordListItem } from '@Entities/records/models';
import { Flex, Table, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { ReactElement, ReactNode, useState } from 'react';

interface IProps {
    OnHoverButton?: (props: IRecordListItem) => ReactNode
    DeleteButton?: (props: IRecordListItem) => ReactNode
    data: IRecordListItem[]
    onRowClick?: (record: IRecordListItem) => void
}

export const RecordTable = ({ data, OnHoverButton, DeleteButton, onRowClick }: IProps): ReactElement => {
    const [hoveredRow, setHoveredRow] = useState<string | null>(null);

    const columns: ColumnsType<IRecordListItem> = [
        {
            title: 'Name',
            dataIndex: 'name',
            width: 355
        },
        {
            title: 'Date',
            dataIndex: 'date',
            width: 355,
            render: (value) => <Typography.Text>{dayjs(value).format('DD/MM/YYYY HH:mm')}</Typography.Text>
        },
        {
            title: 'Context',
            dataIndex: 'context',
            width: 355
        },
        {
            title: 'Created By',
            dataIndex: 'createdBy',
            width: 355
        },
        {
            width: 180,
            minWidth: 180,
            render: (_value, record) => (
                <Flex
                    align={ 'center' }
                    gap={ 8 }
                    justify={ 'flex-end' }
                    style={ { marginLeft: 'auto' } }
                >
                    {hoveredRow === record.id && !!OnHoverButton ? OnHoverButton(record) : null}
                    {!!DeleteButton && DeleteButton(record)}
                </Flex>
            )
        }
    ]

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            onRow={ (record) => ({
                onClick: onRowClick?.bind(null, record),
                onMouseEnter: setHoveredRow.bind(null, record.id),
                onMouseLeave: setHoveredRow.bind(null, null)
            }) }
            rowClassName="clickable-row"
            size={ 'small' }
        />
    )
}

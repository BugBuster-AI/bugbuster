import { Flex, Table, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs'
import { Key, ReactElement, ReactNode, useState } from 'react';

export interface IShortenedListItem {
    id: string;
    name: string;
    date: string;
    context: string
}

interface IProps {
    DeleteButton?: (props: IShortenedListItem) => ReactNode
    data: IShortenedListItem[]
    onSelect?: (props: string[]) => void
    selections?: string[]
}

export const ShortenedRecordTable = ({ data, DeleteButton, onSelect, selections }: IProps): ReactElement => {
    const [selected, setSelected] = useState<string[]>(selections || [])

    const onSelection = (data: Key[]) => {
        onSelect && onSelect(data as string[])
        setSelected(data as string[])
    }

    const columns: ColumnsType<IShortenedListItem> = [
        Table.SELECTION_COLUMN,
        {
            hidden: true,
            dataIndex: 'id',
        },
        {
            title: 'Name',
            dataIndex: 'name',
            width: 270
        },
        {
            title: 'Date',
            dataIndex: 'date',
            width: 270,
            render: (value) => <Typography.Text>{dayjs(value).format('DD/MM/YYYY HH:mm')}</Typography.Text>
        },
        {
            title: 'Context',
            dataIndex: 'context',
            width: 270
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
                    {!!DeleteButton && DeleteButton(record)}
                </Flex>
            )
        }
    ]

    return (
        <Table<IShortenedListItem>
            columns={ columns }
            dataSource={ data }
            pagination={ {
                showTotal: () => null,
                pageSize: 7
            } }
            rowKey={ 'id' }
            rowSelection={ {
                onChange: onSelection,
                selectedRowKeys: selected
            } }
            size={ 'small' }
        />
    )
}

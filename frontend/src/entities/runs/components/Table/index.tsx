import { ClockCircleOutlined } from '@ant-design/icons';
import { StatusBadge } from '@Common/components';
import { useThemeToken } from '@Common/hooks';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ProgressStats } from '@Entities/runs/components/Table/components';
import { IRun } from '@Entities/runs/models';
import { Flex, Table, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableProps } from 'antd/lib';
import dayjs from 'dayjs';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps extends Omit<TableProps, 'columns' | 'dataSource'> {
    data: IRun[]
    renderDropdown?: (prop: IRun) => ReactNode
}

export const RunsTable = ({ data, renderDropdown, ...props }: IProps): ReactElement => {
    const token = useThemeToken()
    const { t } = useTranslation()

    const columns: ColumnsType<IRun> = [
        {
            title: t('grouped_run.table.name'),
            dataIndex: 'name',
            width: 350,
            render: (_value, record) => (
                <Flex align="flex-start" vertical>
                    <Typography.Text>
                        {record.name}
                    </Typography.Text>
                    <Typography.Text style={ { fontSize: '12px', color: token.colorTextDescription } }>
                        {dayjs(record.date).format('YYYY/MM/DD')}
                    </Typography.Text>
                </Flex>
            )
        },
        {
            title: t('grouped_run.table.streams'),
            width: 200,
            dataIndex: 'streams',
            render: (value) => value,
        },
        {
            title: t('grouped_run.table.status'),
            width: 200,
            dataIndex: 'status',
            render: (value) => <StatusBadge status={ value }/>,
            sorter: (a, b) => a.status.localeCompare(b.status),
        },
        {
            title: t('grouped_run.table.deadline'),
            width: 240,
            dataIndex: 'deadline',
            render: (value) => (
                value ?
                    <Typography.Text>
                        {dayjs(value).subtract(1, 'month').format('YYYY/MM/DD HH:mm')}
                    </Typography.Text> : '-'
            ),
            sorter: (a, b) => dayjs(a.deadline).unix() - dayjs(b.deadline).unix(),
        },
        {
            title: t('grouped_run.table.author'),
            width: 240,
            dataIndex: 'author',
            sorter: (a, b) => a.author.localeCompare(b.author)
        },
        {
            title: t('grouped_run.table.time'),
            width: 160,
            dataIndex: 'time',
            render: (value) => (
                <Flex gap={ 8 }>
                    <ClockCircleOutlined style={ { color: token.colorIcon } }/>
                    <Typography.Text>{formatSeconds(Number(value || 0), t)}</Typography.Text>
                </Flex>
            )
        },
        {
            title: t('grouped_run.table.stats'),
            width: 350,
            dataIndex: 'stats',
            render: (value) => <ProgressStats stats={ value }/>,
        },
        {
            width: 100,
            render: renderDropdown ? (_value, data) => renderDropdown(data) : undefined,
            align: 'end'
        }
    ]

    return (
        <Table
            //@ts-ignore
            columns={ columns }
            dataSource={ data }
            rowClassName="clickable-row"
            size={ 'small' }
            { ...props }
        />
    )
}

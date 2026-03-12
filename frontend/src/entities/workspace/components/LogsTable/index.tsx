import { useThemeToken } from '@Common/hooks';
import { IWorkspaceLogItem } from '@Entities/workspace/models/get-workspace-log';
import { Table, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableProps } from 'antd/lib';
import dayjs from 'dayjs';
import React from 'react';

interface ILogsTableProps extends Omit<TableProps<IWorkspaceLogItem>, 'dataSource' | 'columns'> {
    data?: IWorkspaceLogItem[];
}


export const LogsTable: React.FC<ILogsTableProps> = ({ data, ...props }) => {
    const token = useThemeToken()
    const getStatusColor = (status_code: number) => {
        if (status_code.toString().startsWith('2')) {
            return token.colorSuccessText;
        } else if (status_code.toString().startsWith('4')) {
            return token.colorErrorText;
        }

        return 'inherit';
    }

    const columns: ColumnsType<IWorkspaceLogItem> = [
        {
            title: 'User Email',
            dataIndex: 'user_email',
            key: 'user_email',
            width: 300,
        },
        {
            title: 'Timestamp',
            dataIndex: 'timestamp',
            key: 'timestamp',
            width: 300,
            render: (timestamp: string) => dayjs(timestamp).format('YYYY-MM-DD HH:mm:ss'),
        },
        {
            title: 'Username',
            dataIndex: 'user_username',
            key: 'user_username',
            width: 200,

        },
        {
            title: 'Endpoint Name',
            dataIndex: 'endpoint_name',
            key: 'endpoint_name',
            width: 240,

        },
        {
            title: 'Status Code',
            dataIndex: 'status_code',
            key: 'status_code',
            width: 100,

            render: (status_code: number) => (
                <Typography.Text
                    style={ {
                        color: getStatusColor(status_code),
                    } }
                >
                    {status_code}
                </Typography.Text>
            ),
        },
    ];

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            rowKey="id"
            { ...props }
        />
    );
};

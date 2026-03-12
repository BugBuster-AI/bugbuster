import { DeleteOutlined } from '@ant-design/icons';
import { StatusBadge } from '@Common/components/StatusBadge';
import { ERunStatus } from '@Entities/runs/models';
import { Button, Flex, Popconfirm, Table } from 'antd';
import { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { IToken } from '../../models';

interface IProps {
    data?: IToken[];
    loading?: boolean;
    onDelete?: (id: string) => void;
    renderAction?: (record: IToken) => ReactNode;
}

const getTokenStatus = (token: IToken): ERunStatus => {
    if (!token.is_active) return ERunStatus.FAILED;
    if (token.expires_at && dayjs(token.expires_at).isBefore(dayjs())) {
        return ERunStatus.BLOCKED;
    }

    return ERunStatus.PASSED;
};

const getTokenStatusLabel = (token: IToken): string => {
    if (!token.is_active) return 'Inactive';
    if (token.expires_at && dayjs(token.expires_at).isBefore(dayjs())) {
        return 'Expired';
    }

    return 'Active';
}

export const TokensTable = ({ data, loading, onDelete, renderAction }: IProps) => {
    const { t } = useTranslation();

    const columns: ColumnsType<IToken> = [
        {
            title: t('workspace.api_keys.table.name'),
            dataIndex: 'name', // Assuming name exists as per interface
            key: 'name',
            render: (name, record) => name || record.token_id, // Fallback
        },
        {
            title: t('workspace.api_keys.table.status'),
            key: 'status',
            render: (_, record) => {
                const status = getTokenStatus(record);
                const label = getTokenStatusLabel(record);

                return <StatusBadge label={ label } status={ status } />;
            },
        },
        {
            title: t('workspace.api_keys.table.created_at'),
            dataIndex: 'created_at',
            key: 'created_at',
            render: (date) => dayjs(date).format('MM/DD/YY, h:mm A'),
        },
        {
            title: t('workspace.api_keys.table.expires_at'),
            dataIndex: 'expires_at',
            key: 'expires_at',
            render: (date) => (date ? dayjs(date).format('MM/DD/YY, h:mm A') : t('common.noExpiration')),
        },
        {
            title: '',
            key: 'actions',
            align: 'right',
            render: (_, record) => (
                <Flex gap={ 8 } justify="flex-end">
                    {renderAction?.(record)}
                    <Popconfirm
                        description={ t('workspace.api_keys.delete_confirm') }
                        onConfirm={ () => onDelete?.(record.token_id) }
                        style={ { width: 300 } }
                        title={ t('workspace.api_keys.delete_button', 'Delete token?') }
                    >
                        <Button
                            icon={ <DeleteOutlined /> }
                            type="text"
                            danger 
                        />
                    </Popconfirm>
                </Flex>
            ),
        },
    ];

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            loading={ loading }
            pagination={ false }
            rowKey="token_id"
            size="small"
            style={ { width: '100%' } }
        />
    );
};

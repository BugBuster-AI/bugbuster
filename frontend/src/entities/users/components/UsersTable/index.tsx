import { CheckOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { IUserListItem, EUserStatus, IUserProject } from '@Entities/users/models';
import { Avatar, Flex, Table, Tag, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableProps } from 'antd/lib';
import dayjs from 'dayjs';
import head from 'lodash/head';
import size from 'lodash/size';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps extends TableProps {
    data?: IUserListItem[];
    renderAction?: (record: IUserListItem) => ReactNode;
    renderProject?: (record: IUserListItem) => ReactNode;
}

const getStatusIcon = (status: EUserStatus): ReactNode => {
    const iconStyle = { fontSize: '20px' };

    switch (status) {
        case EUserStatus.ACTIVE:
            return <CheckOutlined style={ { color: 'green', ...iconStyle } }/>;
        case EUserStatus.INVITED:
            return <MailOutlined style={ { ...iconStyle } }/>;
        default:
            return null;
    }
};

export const UsersTable = ({ data, renderAction, renderProject, ...props }: IProps): ReactElement => {
    const { t } = useTranslation()
    const token = useThemeToken()

    const formatLastAction = (lastAction: string): string => {
        const now = dayjs();
        const actionTime = dayjs(lastAction);
        const diffMinutes = now.diff(actionTime, 'minute');
        const diffHours = now.diff(actionTime, 'hour');
        const diffDays = now.diff(actionTime, 'day');

        if (diffMinutes < 60) {
            return `${diffMinutes} ${t('users.table.minutes_ago')}`;
        } else if (diffHours < 24) {
            return `${diffHours} ${t('users.table.hours_ago')}`;
        } else {
            return `${diffDays} ${t('users.table.days_ago')}`;
        }
    };

    const columns: ColumnsType<IUserListItem> = [
        {
            title: t('users.table.user'),
            dataIndex: 'email',
            key: 'email',
            width: 542,
            render: (_value, data) => {
                const name =
                    (data?.first_name || data?.last_name) ? `${data.first_name || ''} ${data.last_name || ''}` : '';

                return (
                    <Flex align={ 'center' } gap={ 12 }>
                        <Avatar
                            icon={ !data?.avatar_url ? <UserOutlined/> : undefined }
                            src={ data?.avatar_url }
                            style={ { minWidth: 32 } }/>
                        <Flex vertical>
                            <Typography.Text>{name}</Typography.Text>
                            <Typography.Text style={ { color: token.colorTextDescription } }>
                                {data.email}
                            </Typography.Text>
                        </Flex>
                    </Flex>
                );
            }
        },
        {
            title: t('users.table.status'),
            dataIndex: 'status',
            key: 'status',
            width: 160,
            render: (status: EUserStatus) => getStatusIcon(status),
        },
        {
            title: t('users.table.role'),
            dataIndex: 'role',
            width: 160,
            key: 'role',
        },
        {
            title: t('users.table.role_title'),
            dataIndex: 'role_title',
            width: 160,
            key: 'role_title',
        },
        {
            title: t('users.table.projects'),
            width: 240,
            dataIndex: 'projects',
            key: 'projects',
            render: (value: IUserProject[], record) => {
                const projectsSize = size(value)

                return projectsSize > 0 ?
                    <Flex align={ 'center' }>
                        {renderProject
                            ? renderProject(record)
                            : (
                                <>
                                    <Tag color="default">
                                        {value ? head(value)?.project_name : ''}
                                    </Tag>
                                    {projectsSize > 1 &&
                                        <span style={ { color: token.colorLink } }>+{projectsSize - 1}</span>
                                    }
                                </>
                            )
                        }
                    </Flex> : null
            }
        },
        {
            title: t('users.table.last_action'),
            dataIndex: 'last_action_date',
            width: 160,
            key: 'last_action_date',
            render: (last_action: string) => (last_action ? formatLastAction(last_action) : '-'),
        },
        {
            width: 180,
            align: 'end',
            key: 'actions',
            render: (_text, record) => (renderAction ? renderAction(record) : null),
        },
    ];

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            pagination={ { pageSize: 5 } }
            rowClassName="middle-row-height"
            rowKey="user_id"
            size={ 'middle' }
            style={ { width: '100%' } }
            { ...props }
        />
    );
};

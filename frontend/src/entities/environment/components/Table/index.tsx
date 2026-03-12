import { EditOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { IEnvironmentListItem } from '@Entities/environment/models';
import { Button, Flex, Table, Typography } from 'antd';
import { ColumnsType } from 'antd/es/table';
import upperFirst from 'lodash/upperFirst';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    onEdit?: (record: IEnvironmentListItem) => void
    onDelete?: (record: IEnvironmentListItem) => void
    data: IEnvironmentListItem[]
    loading?: boolean
}

export const EnvironmentTable = ({ onEdit, onDelete, data, loading }: IProps): ReactElement => {
    const { t } = useTranslation()

    const columns: ColumnsType<IEnvironmentListItem> = [
        {
            title: 'Name',
            width: 300,
            dataIndex: 'title'
        },
        {
            title: 'Description',
            width: 300,
            dataIndex: 'description'
        },
        {
            title: 'Browser',
            dataIndex: 'browser',
            width: 300,
            render: (value) => upperFirst(value)
        },
        {
            title: 'Operation System',
            width: 300,
            dataIndex: 'operation_system',
            render: (value) => upperFirst(value)
        },
        {
            title: 'Resolution',
            width: 300,
            dataIndex: 'resolution',
            render: (value: IEnvironmentListItem['resolution']) => (
                <Typography>{value.width} x {value.height}</Typography>
            )
        },
        {
            width: 100,
            minWidth: 100,
            render: (_value, record) => {
                return <Flex align={ 'center' } gap={ 8 } >
                    <Button icon={ <EditOutlined /> } onClick={ onEdit?.bind(null, record) } type={ 'text' }  />
                    <ConfirmButton
                        modalProps={ {
                            title: t('environment_page.modal.delete.title'),
                            onOk: onDelete?.bind(null, record),
                            okText: t('environment_page.modal.delete.buttons.ok'),
                            cancelText: t('environment_page.modal.delete.buttons.cancel'),
                            centered: true,
                            width: 412,
                            okButtonProps: {
                                danger: true
                            }
                        } }>
                        <Typography.Text>
                            {t('environment_page.modal.delete.content',{ name: record.title } )}
                        </Typography.Text>
                    </ConfirmButton>
                </Flex>
            }

        }
    ]

    return <Table columns={ columns } dataSource={ data } loading={ loading } size={ 'small' } />
}

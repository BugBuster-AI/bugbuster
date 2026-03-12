import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { ISharedStep } from '@Entities/shared-steps/models';
import { Button, Flex, Table } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableProps } from 'antd/lib';
import { ReactElement } from 'react';

interface IProps {
    onEdit?: (record: ISharedStep) => void
    onDelete?: (record: ISharedStep) => void
    data: ISharedStep[]
    loading?: boolean
    props?: TableProps<ISharedStep>
}

export const SharedStepsTable = ({ onEdit, onDelete, data, loading, props }: IProps): ReactElement => {

    const columns: ColumnsType<ISharedStep> = [
        {
            title: 'Name',
            width: '50%',
            dataIndex: 'name',
        },
        {
            width: '50%',
            title: 'Description',
            dataIndex: 'description',
        },
        {
            width: 100,
            minWidth: 100,
            render: (_value, record) => {
                return <Flex align={ 'center' } gap={ 8 }>
                    <Button icon={ <EditOutlined/> } onClick={ onEdit?.bind(null, record) } type={ 'text' }/>
                    <Button
                        icon={ <DeleteOutlined/> }
                        onClick={ (e) => {
                            e.stopPropagation()
                            onDelete?.(record)
                        } }
                        type={ 'text' }/>
                </Flex>
            }
        }
    ]

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            loading={ loading }
            rowKey={ 'shared_steps_id' }
            size={ 'small' }
            { ...props }
        />
    )
}


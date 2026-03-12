import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts'; // Предполагаем, что ITableProjectsData содержит данные строки
import { IProjectListItem } from '@Entities/project';
import { Space, Button, Table, Result } from 'antd';
import type { ColumnsType } from 'antd/es/table'; // Импортируем тип ColumnsType
import { Popconfirm } from 'antd/lib';
import { ReactElement, ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

export interface ITableProjectListItem extends IProjectListItem {
    max_streams?: string
}

interface IProps {
    isLoading?: boolean
    data?: ITableProjectListItem[];
    EditButton?: (record: IProjectListItem) => ReactNode,
    DeleteButton?: (record: IProjectListItem) => ReactNode
    error?: string
}

const TableProjects = ({ data, isLoading, error, DeleteButton, EditButton }: IProps): ReactElement => {
    const [open, setOpen] = useState<unknown | null>(null);
    const [confirmLoading, setConfirmLoading] = useState(false);
    const { t } = useTranslation();
    const navigate = useNavigate();

    const showPopconfirm = (index: unknown): void => {
        setOpen(index);
    };

    const handleOk = (index: unknown): void => {
        setConfirmLoading(true);

        //! TODO: Не забыть удалить
        // eslint-disable-next-line no-console
        console.info('delete index', index);

        setTimeout(() => {
            setOpen(null);
            setConfirmLoading(false);
        }, 2000);
    };

    const handleCancel = (): void => {
        setOpen(null);
    };

    const handleEdit = (record: ITableProjectListItem): void => {
        console.info(record)
        /*
         * navigate(`${PATHS.REPOSITORY.INDEX}/${record.id}`)
         * navigate(`${PATHS.PROJECT.INDEX}/${record.project_id}/repository`);
         */
    };

    const columns: ColumnsType<ITableProjectListItem> = [
        {
            title: t('projects_page.index.table.columns.project_name'),
            dataIndex: 'name',
            key: 'name',
        },
        {
            title: t('projects_page.index.table.columns.max_streams'),
            dataIndex: 'max_streams',
            width: 175,
            render: (value) => value
        },
        {
            title: t('projects_page.index.table.columns.suits'),
            dataIndex: 'suite_count',
            key: 'suite_count',
            width: 175,
            render: (value: number): string => t('counts.suits', { count: value }),
        },
        {
            title: t('projects_page.index.table.columns.test_cases'),
            dataIndex: 'case_count',
            key: 'case_count',
            width: 175,
            render: (value: number): string =>
                t('counts.test_cases', { count: value }),
        },
        {
            title: t('projects_page.index.table.columns.runs'),
            dataIndex: 'run_count',
            key: 'run_count',
            width: 175,
            render: (value: number): string => t('counts.runs', { count: value }),
        },
        {
            title: '',
            key: 'actions',
            width: 125,
            align: 'end',
            render: (_: unknown, record: ITableProjectListItem): ReactElement => (
                <Space>
                    {EditButton ? <EditButton { ...record } /> : <Button
                        icon={ <EditOutlined/> }
                        onClick={ handleEdit.bind(this, record) }
                        type="text"
                        variant="filled"
                    />}
                    {DeleteButton ? <DeleteButton { ...record } /> : <Popconfirm
                        description={ t('confirm.delete.projects', {
                            project_name: record.name,
                        }) }
                        okButtonProps={ { loading: confirmLoading } }
                        onCancel={ handleCancel }
                        onConfirm={ handleOk.bind(this, record.project_id) }
                        open={ open === record.project_id }
                        title={ record.name }
                    >
                        <Button
                            icon={ <DeleteOutlined/> }
                            onClick={ showPopconfirm.bind(this, record.project_id) }
                            type="text"
                            variant="filled"
                        />
                    </Popconfirm>}
                </Space>
            ),
        },
    ];

    if (!!error) {
        return <Result status={ 'error' } title={ error }/>
    }

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            loading={ isLoading }
            onRow={ (data) => ({
                onClick: () => {
                    navigate(`${PATHS.PROJECT.INDEX}/${data.project_id}/repository`)

                }
            }) }
            rowClassName="clickable-row"
            rowKey="id"
            size={ 'small' }/>
    );
};

export default TableProjects;

import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { useProjectStore } from '@Entities/project/store';
import { IVariableKit } from '@Entities/variable/models';
import { variableQueries } from '@Entities/variable/queries';
import { DeleteVariableKit, EditVariableKit } from '@Features/variable';
import { useQuery } from '@tanstack/react-query';
import { Flex, Result, Table } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

interface IProps {
    search?: string
}

export const VariableKitTable = ({ search }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage' })
    const project = useProjectStore((state) => state.currentProject)
    const {
        data,
        isLoading,
        error
    } = useQuery(variableQueries.kitList({ project_id: project?.project_id!, search }, { enabled: !!project }))

    const navigate = useNavigate()

    const columns: ColumnsType<IVariableKit> = [
        {
            title: t('list.name'),
            dataIndex: 'variables_kit_name',
            key: 'name',
        },
        {
            title: t('list.description'),
            dataIndex: 'variables_kit_description',
            key: 'description',
        },
        {
            width: 100,
            key: 'actions',
            onCell: () => ({
                onClick: (e) => e.stopPropagation()
            }),
            render: (_, record) => (record.editable ? <Flex gap={ 8 }>
                <EditVariableKit data={ record }/>
                <DeleteVariableKit data={ record }/>
            </Flex> : null),
        }
    ]

    const errorMessage = getErrorMessage({
        error,
        needConvertResponse: true
    })

    if (errorMessage) {
        return <Result status="error" title={ errorMessage }/>
    }

    return (
        <Table
            columns={ columns }
            dataSource={ data }
            loading={ isLoading }
            onRow={ (record) => ({ onClick: () => navigate(`${record.variables_kit_id}`) }) }
            pagination={ false }
            rowClassName="clickable-row"
            rowKey={ 'variables_kit_id' }
            size={ 'small' }
        />
    )

}

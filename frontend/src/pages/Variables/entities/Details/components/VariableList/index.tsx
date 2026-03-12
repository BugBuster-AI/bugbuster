import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { IVariable } from '@Entities/variable/models';
import { VariableType } from '@Entities/variable/models/types';
import { DeleteVariable } from '@Pages/Variables/entities/Details/components/DeleteVariable';
import { UpdateVariable } from '@Pages/Variables/entities/Details/components/EditVariable';
import { Flex, Result, Table, Tag } from 'antd';
import { ColumnsType } from 'antd/es/table';
import upperFirst from 'lodash/upperFirst';
import { useTranslation } from 'react-i18next';

interface IProps {
    isLoading: boolean,
    data: IVariable[]
    error?: Error
}

const typeColors = {
    [VariableType.simple]: 'blue-inverse',
    [VariableType.time]: 'orange-inverse'
}

export const VariableListTable = ({ data, isLoading, error }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage.details' })

    const columns: ColumnsType<IVariable> = [
        {
            title: t('list.name'),
            dataIndex: 'variable_name',
            key: 'name',
        },
        {
            title: t('list.type'),
            dataIndex: ['variable_config', 'type'],
            key: 'type',
            render: (_, record) => {
                const color = record.variable_config?.type && typeColors?.[record.variable_config.type];

                return (
                    <Tag
                        color={ color as string }
                        style={ { fontWeight: 500 } } >
                        {upperFirst(record.variable_config.type ?? '')}
                    </Tag>
                )
            }
        },
        {
            title: t('list.value'),
            dataIndex: 'variable_value',
            key: 'value',
            width: `40%`,
            render: (_, record) => {
                const needTag = record.variable_config.type === VariableType.time
                const isConst = record.variable_config?.is_const
                const color = isConst ? 'purple-inverse' : 'cyan-inverse'
                const name = isConst ? t('variableValueTypes.constant') : t('variableValueTypes.dynamic')

                return (
                    <Flex gap={ 8 } vertical>
                        <span>{record.computed_value}</span>
                        {needTag && (
                            <Tag
                                color={ `${color}` } 
                                style={ { width: 'fit-content' } } 
                            >
                                {name}
                            </Tag>
                        )}
                    </Flex>
                )
            }
        },
        {
            title: t('list.description'),
            dataIndex: 'variable_description',
            key: 'description',
        },
        {
            width: 100,
            key: 'actions',
            onCell: () => ({
                onClick: (e) => e.stopPropagation()
            }),
            render: (_, record) => <Flex gap={ 8 }>
                <UpdateVariable data={ record }/>
                <DeleteVariable data={ record }/>
            </Flex>,
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
            pagination={ false }
            size={ 'small' }
        />
    )

}

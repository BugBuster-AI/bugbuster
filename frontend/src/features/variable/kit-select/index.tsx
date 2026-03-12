import { AsyncSelect } from '@Common/components';
import { IVariableKit } from '@Entities/variable/models';
import { variableQueries } from '@Entities/variable/queries';
import { SelectProps } from 'antd';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps extends SelectProps {
    projectId: string
    enableSearch?: boolean
}

export const VariableKitSelect = ({ projectId, enableSearch = true, ...props }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variables' })
    const [searchValue, setSearchValue] = useState('')

    const queryOptions = useMemo(() => {
        return variableQueries.kitList({
            project_id: projectId,
            search: searchValue || undefined
        }, { enabled: !!projectId })
    }, [projectId, searchValue])

    return (
        <AsyncSelect<IVariableKit>
            enableSearch={ enableSearch }
            keyIndex={ 'variables_kit_name' }
            labelIndex={ 'variables_kit_name' }
            onSearchChange={ setSearchValue }
            placeholder={ t('select.placeholder') }
            queryOptions={ queryOptions }
            { ...props }
        />
    )
}

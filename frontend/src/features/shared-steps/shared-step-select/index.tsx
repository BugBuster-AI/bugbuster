import { AsyncSelect } from '@Common/components';
import { useProjectStore } from '@Entities/project/store';
import { sharedStepsQueries } from '@Entities/shared-steps';
import { SelectProps } from 'antd';
import { ComponentProps, useState } from 'react';

interface IProps extends SelectProps, Pick<ComponentProps<typeof AsyncSelect>, 'onLoadData'> {
    enableSearch?: boolean
}

export const SharedStepSelect = ({ enableSearch = true, ...props }: IProps) => {
    const { currentProject } = useProjectStore()
    const [searchValue, setSearchValue] = useState('')

    const queryOptions = sharedStepsQueries.list({
        project_id: currentProject?.project_id!,
        search: searchValue || undefined
    })

    return (
        <AsyncSelect
            enableSearch={ enableSearch }
            keyIndex={ 'shared_steps_id' }
            labelIndex={ 'name' }
            onSearchChange={ setSearchValue }
            placeholder={ 'Shared step...' }
            queryOptions={ queryOptions }
            { ...props }
        />
    )
}

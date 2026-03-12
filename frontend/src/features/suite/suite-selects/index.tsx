import { useProjectStore } from '@Entities/project/store';
import { suiteQueries } from '@Entities/suite/queries';
import { treeSuiteAdapter } from '@Entities/suite/utils';
import { useQuery } from '@tanstack/react-query';
import { TreeSelect } from 'antd';
import head from 'lodash/head';
import { useMemo } from 'react';

interface IProps {
    value?: string,
    onChange?: (value: string) => void
    placeholder?: string
}

export const SuiteSelect = ({ onChange, value, placeholder, ...props }: IProps) => {
    const project = useProjectStore().currentProject
    const projectId = project?.project_id
    const { data } = useQuery(suiteQueries.userTree({ project_id: projectId }, !!projectId))

    const adaptedData = useMemo(() => treeSuiteAdapter(head(data)?.suites), [data])

    return (
        <TreeSelect
            dropdownStyle={ { maxHeight: 400, overflow: 'auto' } }
            onChange={ onChange }
            placeholder={ placeholder || 'Project root' }
            style={ { width: '100%' } }
            treeData={ adaptedData }
            value={ value }
            allowClear
            treeDefaultExpandAll
            { ...props }
        />
    )
}

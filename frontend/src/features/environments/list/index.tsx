import { asyncHandler } from '@Common/utils';
import { EnvironmentTable, IEnvironmentListItem } from '@Entities/environment';
import { envQueries } from '@Entities/environment/queries';
import { useDeleteEnv } from '@Entities/environment/queries/mutations';
import { useQuery } from '@tanstack/react-query';
import { ReactElement } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

export const EnvironmentsList = (): ReactElement => {
    const { id } = useParams()
    const { data, isLoading } = useQuery({
        ...envQueries.envList(id!),
        enabled: !!id
    })
    const navigate = useNavigate()
    const { mutateAsync } = useDeleteEnv(id!)

    const handleDelete = (record: IEnvironmentListItem) => {
        asyncHandler(mutateAsync.bind(null, record.environment_id))
    }

    const handleEdit = (record: IEnvironmentListItem) => {
        navigate(`edit/${record.environment_id}`)
    }

    return (
        <EnvironmentTable
            data={ data || [] }
            loading={ isLoading }
            onDelete={ handleDelete }
            onEdit={ handleEdit }
        />
    )
}


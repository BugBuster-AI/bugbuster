import { EnvironmentsApi } from '@Entities/environment/api';
import { ICreateEnvironmentPayload, IUpdateEnvironmentPayload } from '@Entities/environment/models';
import { envQueries } from '@Entities/environment/queries';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const envApi = EnvironmentsApi.getInstance()

export const useCreateEnv = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: ICreateEnvironmentPayload) => envApi.createEnv(data),
        onSuccess: (_, data) => {
            const project_id = data.project_id

            queryClient.invalidateQueries(envQueries.envList(project_id))
        }
    })
}

export const useUpdateEnv = (project_id: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ id, data }: { id: string, data: IUpdateEnvironmentPayload }) => envApi.updateEnv({ id, data }),
        onSuccess: () => {
            queryClient.invalidateQueries(envQueries.envList(project_id))
        }
    })
}

export const useDeleteEnv = (project_id: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (id: string) => envApi.deleteEnv(id),
        onSuccess: () => {
            queryClient.invalidateQueries(envQueries.envList(project_id))
        }
    })
}

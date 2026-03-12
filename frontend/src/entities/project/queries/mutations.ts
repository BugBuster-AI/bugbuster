import { ICreateProjectPayload, IProjectWithId } from '@Entities/project';
import { ProjectApi } from '@Entities/project/api';
import { projectQueries } from '@Entities/project/queries';
import { projectKeys } from '@Entities/project/queries/query-keys.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const projectsApi = ProjectApi.getInstance();

export const useCreateProject = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [projectKeys.index, projectKeys.create],
        mutationFn: (data: ICreateProjectPayload) => projectsApi.create(data),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: projectQueries.all()
            });
        }
    })
};

export const useUpdateProject = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [projectKeys.index, projectKeys.update],
        mutationFn: (data: IProjectWithId) => projectsApi.update(data),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: projectQueries.all()
            });
        }
    })
};

export const useDeleteProject = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [projectKeys.index, projectKeys.delete],
        mutationFn: (id: string) => projectsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: projectQueries.all()
            });
        }
    })
};

import { SharedStepsApi } from '@Entities/shared-steps/api';
import { ICreateSharedStepPayload, IGetSharedStepByIdRequest } from '@Entities/shared-steps/models';
import { IUpdateSharedStepRequest } from '@Entities/shared-steps/models/update';
import { sharedStepsQueries } from '@Entities/shared-steps/queries';
import { sharedStepsKeys } from '@Entities/shared-steps/queries/query-keys';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const sharedStepsApi = SharedStepsApi.getInstance()

export const useCreateSharedStep = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: ICreateSharedStepPayload) => sharedStepsApi.create(data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries(sharedStepsQueries.list({ project_id: variables.project_id }));
        },
    });
};

export const useUpdateSharedStep = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: IUpdateSharedStepRequest) => sharedStepsApi.update(data),
        onSuccess: (_, variables) => {
            queryClient.invalidateQueries({ queryKey: [...sharedStepsQueries.all(), sharedStepsKeys.list] });
            queryClient.invalidateQueries(sharedStepsQueries.byId({ id: variables.shared_steps_id }));
        },
    });
};

export const useDeleteSharedStep = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationKey: [sharedStepsKeys.delete],
        mutationFn: (params: IGetSharedStepByIdRequest) => sharedStepsApi.delete(params),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: [...sharedStepsQueries.all(), sharedStepsKeys.list] });
        },
    });
};

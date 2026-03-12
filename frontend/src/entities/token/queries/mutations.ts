import { useMutation, useQueryClient } from '@tanstack/react-query';
import { TokenApi } from '../api';
import { tokenQueryKeys } from './query-keys';
import { ICreateTokenPayload, IUpdateTokenPayload } from '../models';

const tokenApi = TokenApi.getInstance();

export const useCreateTokenMutation = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: ICreateTokenPayload) => tokenApi.create(payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: tokenQueryKeys.all });
        },
    });
};

export const useUpdateTokenMutation = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (payload: IUpdateTokenPayload) => tokenApi.update(payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: tokenQueryKeys.all });
        }
    });
};

export const useActivateTokenMutation = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => tokenApi.activate(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: tokenQueryKeys.all });
        }
    });
};

export const useDeactivateTokenMutation = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => tokenApi.deactivate(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: tokenQueryKeys.all });
        }
    });
};

export const useDeleteTokenMutation = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => tokenApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: tokenQueryKeys.all });
        },
    });
};

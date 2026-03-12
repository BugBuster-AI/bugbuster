import { VariableApi } from '@Entities/variable/api';
import { ICreateVariableKitRequest, IUpdateVariableKitRequest, IVariable } from '@Entities/variable/models';
import { ICreateVariableRequest } from '@Entities/variable/models/create-variable.dto.ts';
import { IDeleteVariableKitRequest } from '@Entities/variable/models/delete-variable-kit.dto.ts';
import { IDeleteVariableRequest } from '@Entities/variable/models/delete-variable.dto.ts';
import { IUpdateVariableRequest } from '@Entities/variable/models/update-variable.dto.ts';
import { variableQueries } from '@Entities/variable/queries/index.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const variableApi = VariableApi.getInstance()

export const useCreateVariableKit = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: ICreateVariableKitRequest) => variableApi.createVariableKit(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries(variableQueries.kitList({ project_id: data.project_id }));
        },
    })
}

export const useUpdateVariableKit = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IUpdateVariableKitRequest) => variableApi.updateVariableKit(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries(variableQueries.kitList({ project_id: data.project_id }));
            queryClient.invalidateQueries(variableQueries.kitItem({ variables_kit_id: data.variables_kit_id }));
        },
    })
}

export const useDeleteVariableKit = (projectId: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IDeleteVariableKitRequest) => variableApi.deleteVariableKit(data),
        onSuccess: (_, payload) => {
            queryClient.invalidateQueries(variableQueries.kitList({ project_id: projectId }));
            queryClient.invalidateQueries(variableQueries.kitItem({ variables_kit_id: payload.variables_kit_id }));
        },
    })
}


export const useCreateVariable = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: ICreateVariableRequest) => variableApi.createVariable(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries(variableQueries.variableList({ variables_kit_id: data.variables_kit_id }));
        },
    })
}

export const useUpdateVariable = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IUpdateVariableRequest) => variableApi.updateVariable(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries(variableQueries.variableList({ variables_kit_id: data.variables_kit_id }));
        },
    })
}

export const useDeleteVariable = (kitId?: string) => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IDeleteVariableRequest) => variableApi.deleteVariable(data),
        onSuccess: () => {
            queryClient.invalidateQueries(variableQueries.variableList({ variables_kit_id: kitId || '' }));
        },
    })
}

export const usePrecalcVariable = () => {
    return useMutation({
        mutationFn: (data: Omit<IVariable, 'computed_value'>) => variableApi.computeVariableValue(data),  
    })
}

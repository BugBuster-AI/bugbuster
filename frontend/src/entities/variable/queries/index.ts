import { VariableApi } from '@Entities/variable/api';
import {
    IGetKitVariableByIdRequest,
    IGetKitVariableByIdResponse,
    IGetListVariableKitsRequest, IVariable,
    IVariableKit
} from '@Entities/variable/models';
import { IGetVariableRequest } from '@Entities/variable/models/get-variable.dto.ts';
import {
    IGetVariableListResponse,
    IGetVariablesListByNameRequest,
    IGetVariablesListRequest
} from '@Entities/variable/models/get-variables-list.dto.ts';
import { variableQueryKeys } from '@Entities/variable/queries/queryKeys.ts';
import { QueryObserverOptions, queryOptions } from '@tanstack/react-query';
import trim  from 'lodash/trim';

const variableApi = VariableApi.getInstance()

export const getSearchParams = <T extends {search?: string}>(params: T) => {
    if (trim(params.search) === '') {
        delete params.search
    }
    
    return params
}

const variableQueries = {

    kitItem: (
        params: IGetKitVariableByIdRequest,
        options?: Partial<QueryObserverOptions<IGetKitVariableByIdResponse, Error>>
    ) =>
        queryOptions({
            queryFn: () => variableApi.getVariableKitById(params),
            queryKey: [variableQueryKeys.kitItem, params.variables_kit_id],
            enabled: !!params?.variables_kit_id,
            ...options
        }),
    kitList: (params: IGetListVariableKitsRequest, options?: Partial<QueryObserverOptions<IVariableKit[], Error>>) =>
        queryOptions({
            queryFn: () => variableApi.getListVariableKits(getSearchParams(params)),
            queryKey: [variableQueryKeys.kitList, getSearchParams(params)],
            ...options
        }),

    variableList: (
        params: IGetVariablesListRequest,
        options?: Partial<QueryObserverOptions<IGetVariableListResponse, Error>>) =>
        queryOptions({
            queryFn: () => variableApi.getListVariables(getSearchParams(params)),
            queryKey: [variableQueryKeys.variableList, getSearchParams(params)],
            ...options
        }),

    variableListByName: (
        params: IGetVariablesListByNameRequest,
        options?: Partial<QueryObserverOptions<IGetVariableListResponse, Error>>
    ) =>
        queryOptions({
            queryFn: () => variableApi.getListVariablesByName(params),
            queryKey: [variableQueryKeys.variableList, params.variables_kit_name, params.project_id],
            ...options
        }),

    variableItem: (params: IGetVariableRequest, options?: Partial<QueryObserverOptions<IVariable, Error>>) =>
        queryOptions({
            queryFn: () => variableApi.getVariableById(params),
            queryKey: [variableQueryKeys.variableItem, params.variable_details_id],
            enabled: !!params?.variable_details_id,
            ...options
        })
}

export * from './queryKeys.ts'
export * from './mutations.ts'
export { variableQueries };

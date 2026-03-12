import { $api } from '@Common/api';
import {
    IUpdateVariableKitRequest,
    IUpdateVariableKitResponse,
    IVariable,
    IVariableKit
} from '@Entities/variable/models';
import {
    ICreateVariableKitRequest,
    ICreateVariableKitResponse
} from '@Entities/variable/models/create-variable-kit.dto.ts';
import { ICreateVariableRequest, ICreateVariableResponse } from '@Entities/variable/models/create-variable.dto.ts';
import { IDeleteVariableKitRequest } from '@Entities/variable/models/delete-variable-kit.dto.ts';
import { IDeleteVariableRequest } from '@Entities/variable/models/delete-variable.dto.ts';
import {
    IGetKitVariableByIdRequest,
    IGetKitVariableByIdResponse
} from '@Entities/variable/models/get-kit-variable-by-id.dto.ts';
import {
    IGetListVariableKitsRequest,
} from '@Entities/variable/models/get-list-variable-kits.dto.ts';
import { IGetVariableRequest, IGetVariableResponse } from '@Entities/variable/models/get-variable.dto.ts';
import {
    IGetVariableListResponse,
    IGetVariablesListByNameRequest,
    IGetVariablesListRequest
} from '@Entities/variable/models/get-variables-list.dto.ts';
import { IUpdateVariableRequest } from '@Entities/variable/models/update-variable.dto.ts';

export class VariableApi {
    private static instance: VariableApi | null

    public static getInstance (): VariableApi {
        if (!this.instance) {
            this.instance = new VariableApi()

            return this.instance
        }

        return this.instance
    }

    async getListVariableKits (params: IGetListVariableKitsRequest): Promise<IVariableKit[]> {
        return (await $api.get(`variables/get_list_variables_kit`, { params })).data
    }

    async getVariableKitById ({ variables_kit_id }: IGetKitVariableByIdRequest): Promise<IGetKitVariableByIdResponse> {
        return (await $api.get(`variables/${variables_kit_id}`)).data
    }

    async createVariableKit (data: ICreateVariableKitRequest): Promise<ICreateVariableKitResponse> {
        return (await $api.post(`variables`, data)).data
    }

    async updateVariableKit ({
        variables_kit_id,
        ...data
    }: IUpdateVariableKitRequest): Promise<IUpdateVariableKitResponse> {
        return (await $api.put(`variables/${variables_kit_id}`, data)).data
    }

    async deleteVariableKit ({ variables_kit_id }: IDeleteVariableKitRequest): Promise<string> {
        return (await $api.delete(`variables/${variables_kit_id}`)).data
    }

    async getListVariables (params: IGetVariablesListRequest): Promise<IGetVariableListResponse> {
        return (await $api.get(`variables_details/get_list_variables_by_variables_kit_id`, { params })).data
    }

    async getListVariablesByName (params: IGetVariablesListByNameRequest): Promise<IGetVariableListResponse> {
        return (await $api.get(`variables_details/get_list_variables_by_variables_kit_name`, { params })).data
    }

    async getVariableById ({ variable_details_id }: IGetVariableRequest): Promise<IGetVariableResponse> {
        return (await $api.get(`variables_details/${variable_details_id}`)).data
    }

    async createVariable (data: ICreateVariableRequest): Promise<ICreateVariableResponse> {
        return (await $api.post(`variables_details`, data)).data
    }


    async updateVariable ({ variable_details_id, ...data }: IUpdateVariableRequest): Promise<ICreateVariableResponse> {
        return (await $api.put(`variables_details/${variable_details_id}`, data)).data
    }

    async deleteVariable ({ variable_details_id }: IDeleteVariableRequest): Promise<string> {
        return (await $api.delete(`variables_details/${variable_details_id}`)).data
    }

    async computeVariableValue (data: Omit<IVariable, 'computed_value'>): Promise<IVariable> {
        return (await $api.post(`variables_details/precalc_new_variable`, data)).data
    }
}

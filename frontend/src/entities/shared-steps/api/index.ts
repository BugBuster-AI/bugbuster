import { $api } from '@Common/api';
import {
    ICreateSharedStepPayload, IGetSharedStepsListByNameRequest,
    IGetSharedStepsListRequest,
    IGetSharedStepsListResponse,
    ISharedStep
} from '@Entities/shared-steps/models';
import { IGetSharedStepByIdRequest } from '@Entities/shared-steps/models/get-by-id.ts';
import { IUpdateSharedStepRequest } from '@Entities/shared-steps/models/update.ts';

export class SharedStepsApi {
    private static instance: SharedStepsApi | null

    public static getInstance (): SharedStepsApi {
        if (!this.instance) {
            this.instance = new SharedStepsApi()

            return this.instance
        }

        return this.instance
    }

    async getList (params: IGetSharedStepsListRequest): Promise<IGetSharedStepsListResponse> {
        return (await $api.get('/shared_steps/get_list_shared_steps_by_project_id', {
            params
        })).data
    }

    async create (data: ICreateSharedStepPayload): Promise<ISharedStep> {
        return (await $api.post('/shared_steps', data)).data
    }

    async getById (params: IGetSharedStepByIdRequest): Promise<ISharedStep> {
        return (await $api.get(`/shared_steps/${params.id}`)).data
    }

    async getListByName (params: IGetSharedStepsListByNameRequest): Promise<IGetSharedStepsListResponse> {
        return (await $api.get('/shared_steps/get_list_shared_steps_by_name', {
            params
        })).data
    }

    async delete (params: IGetSharedStepByIdRequest): Promise<string> {
        return (await $api.delete(`/shared_steps/${params.id}`)).data
    }

    async update (data: IUpdateSharedStepRequest): Promise<ISharedStep> {
        return (await $api.put(`/shared_steps`, data)).data
    }
}

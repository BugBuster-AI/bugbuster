import { $api } from '@Common/api';
import {
    IChangeSuitePosition,
    ICreateSuitePayload,
    IUpdateSuite,
    IUserTree,
    IUserTreePayload
} from '@Entities/suite/models';

export class SuiteApi  {
    private static instance: SuiteApi | null

    public static getInstance (): SuiteApi {
        if (!this.instance) {
            this.instance = new SuiteApi()

            return this.instance
        }

        return this.instance
    }

    public async getUserTree (params?: IUserTreePayload): Promise<IUserTree[]> {
        return (await $api.get('content/user_tree', { params })).data
    }

    public async updateSuite (data: IUpdateSuite): Promise<IUpdateSuite> {
        return (await $api.put('content/suite', data)).data
    }

    public async createSuite (data: ICreateSuitePayload): Promise<ICreateSuitePayload> {
        return (await $api.post('content/suite', data)).data
    }

    public async delete (id: string): Promise<void> {
        return (await $api.delete(`content/suite/${id}`)).data
    }

    public async changePosition (data: IChangeSuitePosition): Promise<{status: string}> {
        return (await $api.put('content/change_suite_position', null, { params: data })).data
    }
}

import { $api } from '@Common/api';
import {
    ICreateEnvironmentPayload, IEnvironmentListItem, IUpdateEnvironmentPayload
} from '@Entities/environment/models';

export class EnvironmentsApi {
    private static instance: EnvironmentsApi | null

    public static getInstance (): EnvironmentsApi {
        if (!this.instance) {
            this.instance = new EnvironmentsApi()

            return this.instance
        }

        return this.instance
    }

    async getBrowsers (): Promise<string[]> {
        return (await $api.get('environments/get_list_browsers')).data
    }

    async getOs (): Promise<string[]> {
        return (await $api.get('environments/get_list_os')).data
    }

    async getEnvList (project_id: string): Promise<IEnvironmentListItem[]> {
        return (await $api.get('environments/get_list_environments', { params: { project_id } })).data
    }

    async getEnvById (id: string): Promise<IEnvironmentListItem> {
        return (await $api.get(`environments/${id}`)).data
    }

    async createEnv (data: ICreateEnvironmentPayload): Promise<IEnvironmentListItem> {
        return (await $api.post(`environments`, data)).data
    }

    async updateEnv ({ id, data }: { id: string, data: IUpdateEnvironmentPayload }): Promise<IEnvironmentListItem> {
        return (await $api.put(`environments/${id}`, data)).data
    }

    async deleteEnv (id: string): Promise<void> {
        return (await $api.delete(`environments/${id}`)).data
    }
}

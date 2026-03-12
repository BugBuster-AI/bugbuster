import { $api } from '@Common/api';
import { IFullHappypass, IGetHappypassPayload, IHappyPassListItem } from '@Entities/records/models';
import { IGenerateHappypassPayload } from '@Entities/records/models/generate-happypass.ts';

export class RecordsApi {
    private static instance: RecordsApi | null

    public static getInstance (): RecordsApi {
        if (!this.instance) {
            this.instance = new RecordsApi()

            return this.instance
        }

        return this.instance
    }

    public async getListHappypass ({ projectId }: { projectId: string }): Promise<IHappyPassListItem[]> {
        return (await $api.get('records/list_happypass', { params: { project_id: projectId } })).data
    }

    public async getHappypass (params?: IGetHappypassPayload): Promise<IFullHappypass> {
        return (await $api.get(`records/happypass`, { params })).data
    }

    public async deleteHappypass (id: string): Promise<void> {
        return (await $api.delete(`records/happypass/${id}`)).data
    }

    public async generateHappypass (data: IGenerateHappypassPayload): Promise<void> {
        return (await $api.put(`records/happypass_autosop_generate`, {}, { params: data })).data
    }
}

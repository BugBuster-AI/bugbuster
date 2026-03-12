import { $api } from '@Common/api';
import { IMedia } from '@Entities/runs/models';

export class ToolsApi {
    private static instance: ToolsApi | null

    public static getInstance (): ToolsApi {
        if (!this.instance) {
            this.instance = new ToolsApi()

            return this.instance
        }

        return this.instance
    }

    async uploadImages (): Promise<IMedia> {
        return (await $api.post('tools/upload_images')).data
    }

    async uploadFiles (formData: FormData): Promise<IMedia[]> {
        return (await $api.post('tools/upload_files', formData, {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'multipart/form-data'
            }
        })).data;
    }
}

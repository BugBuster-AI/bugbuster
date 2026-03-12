import { $api } from '@Common/api';
import { IStreamsStatList } from '@Entities/stream/models';

export class StreamsApi {
    private static instance: StreamsApi | null

    public static getInstance (): StreamsApi {
        if (!this.instance) {
            this.instance = new StreamsApi()

            return this.instance
        }

        return this.instance
    }

    async getStreamsStatistic (): Promise<IStreamsStatList> {
        return (await $api.get('runs/get_streams_statistics')).data
    }

}

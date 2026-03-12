import { $api } from '@Common/api';
import { IToken, ICreateTokenPayload, IUpdateTokenPayload } from '../models';

export class TokenApi {
    private static instance: TokenApi | null;

    public static getInstance (): TokenApi {
        if (!this.instance) {
            this.instance = new TokenApi();

            return this.instance;
        }

        return this.instance;
    }

    async getAll (): Promise<IToken[]> {
        return (await $api.get('tokens')).data;
    }

    async create (payload: ICreateTokenPayload): Promise<IToken> {
        const params: Record<string, any> = {
            name: payload.name
        };

        if (payload.expires_at) {
            params.expires_at = new Date(payload.expires_at).toISOString().split('T')[0];
        }

        return (await $api.post('tokens', { ...params },)).data;
    }

    async update (payload: IUpdateTokenPayload): Promise<IToken> {
        const params: Record<string, any> = {
            name: payload.name
        };

        if (payload.expires_at) {
            params.expires_at = new Date(payload.expires_at).toISOString().split('T')[0];
        } else {
            params.expires_at = null
        }

        return (await $api.put(`tokens/${payload.token_id}`, { ...params })).data;
    }

    async activate (id: string): Promise<IToken> {
        return (await $api.post(`tokens/${id}/activate`)).data;
    }

    async deactivate (id: string): Promise<IToken> {
        return (await $api.post(`tokens/${id}/deactivate`)).data;
    }

    async delete (id: string): Promise<void> {
        return (await $api.delete(`tokens/${id}`)).data;
    }
}

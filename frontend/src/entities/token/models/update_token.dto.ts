import { ICreateTokenPayload } from './token';

export interface IUpdateTokenPayload extends ICreateTokenPayload {
    token_id: string;
    name?: string
}

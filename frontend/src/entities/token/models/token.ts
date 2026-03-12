export interface IToken {
    token_id: string;
    token: string;
    is_active: boolean;
    expires_at: string | null;
    created_at: string;
    name?: string;
}

export interface ICreateTokenPayload {
    name?: string;
    expires_at?: string;
}

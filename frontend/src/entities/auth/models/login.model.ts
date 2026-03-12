export interface ILoginPayload {
    email: string;
    password: string;
}

export interface ILoginResponse {
    access_token: string;
    token_type: string;
    user_id: string;
    roles: string[]
    picture?: string | null
}

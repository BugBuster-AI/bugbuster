export interface IResetPasswordPayload {
    email: string
    language: 'ru' | 'en'
}

export interface IPasswordResetConfirm {
    token: string;
    new_password: string
}

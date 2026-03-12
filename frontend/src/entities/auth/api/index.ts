import { $api } from '@Common/api';
import {
    ILoginPayload,
    ILoginResponse,
    IPasswordResetConfirm,
    IResetPasswordPayload,
    ISignupPayload
} from '@Entities/auth';
import { IPasswordChangePayload } from '@Entities/auth/models/password-change.ts';
import { IUser } from '@Entities/auth/models/user.model.ts';

export class AuthApi {
    private static instance: AuthApi | null

    public static getInstance (): AuthApi {
        if (!this.instance) {
            this.instance = new AuthApi()

            return this.instance
        }

        return this.instance
    }

    async getUser (): Promise<IUser> {
        return (await $api.get('auth/users/me')).data
    }

    async login (data: ILoginPayload): Promise<ILoginResponse> {
        return (await $api.post('auth/signin', { ...data },
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            })).data
    }

    async singup (data: ISignupPayload): Promise<ILoginResponse> {
        return (await $api.post('auth/signup', { ...data }))
    }

    async requestResetPassword (data: IResetPasswordPayload): Promise<string> {
        return (await $api.post(`auth/password_reset_request`, { ...data })).data
    }

    async passwordChange (data: IPasswordChangePayload): Promise<string> {
        return (await $api.post(`auth/password_change`, { ...data })).data
    }

    async resetPasswordConfirm (data: IPasswordResetConfirm): Promise<string> {
        return (await $api.post(`auth/user_password_reset_confirm`, { ...data }))
    }

    async fastSignup (email: string): Promise<string> {
        return (await $api.post(`auth/fast_signup`, { email })).data
    }
}

import { createSelectors } from '@Common/lib';
import { EStatus, IError } from '@Common/types';
import { clearToken, setToken } from '@Common/utils/token.ts';
import { ILoginPayload } from '@Entities/auth';
import { AuthApi } from '@Entities/auth/api';
import { IUser } from '@Entities/auth/models/user.model.ts';
import { AxiosError } from 'axios';
import { devtools } from 'zustand/middleware'
import { create } from 'zustand/react';
import { StateCreator } from 'zustand/vanilla';

export enum ELoginStatus {
    IDLE = 'idle',
    UN_AUTH = 'unauth',
    IS_AUTH = 'auth',
    LOADING = 'loading'
}

interface IState {
    error: string | null
    status: EStatus
    user: IUser | null
    loginStatus: ELoginStatus
}

interface IActions {
    login: (data: ILoginPayload) => Promise<void>
    getUser: () => Promise<void>
    logout: () => void
}

type TAuthStore = IActions & IState

const authApi = AuthApi.getInstance()

const authSlice: StateCreator<
    TAuthStore,
    [['zustand/devtools', never]],
    []
> = (set) => ({
    error: null,
    user: null,
    status: EStatus.IDLE,
    loginStatus: ELoginStatus.IDLE,

    getUser: async (): Promise<void> => {
        set({ loginStatus: ELoginStatus.LOADING })

        try {
            const user = await authApi.getUser()

            set({ user, loginStatus: ELoginStatus.IS_AUTH })
        } catch {
            set({ user: null, loginStatus: ELoginStatus.UN_AUTH })
            localStorage.removeItem('user-picture')
            clearToken()
        }
    },

    login: async (data): Promise<void> => {
        set({ status: EStatus.LOADING })

        try {
            const loginData = await authApi.login(data)

            setToken(loginData.access_token)

            set({ error: null, status: EStatus.SUCCESS })
        } catch (e: unknown) {
            const axiosError = e as AxiosError<IError>
            const error = axiosError?.response?.data.detail || 'Something went wrong...'

            localStorage.removeItem('user-picture')

            set({ error, status: EStatus.ERROR })
        }
    },

    logout: (): void => {
        clearToken()
        localStorage.removeItem('user-picture')
        set({ user: null, loginStatus: ELoginStatus.UN_AUTH })
    }
})

const withDevtools = devtools(authSlice, { name: 'Auth Store' })
const store = create(withDevtools)

export const useAuthStore = createSelectors(store)


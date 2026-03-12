export interface IRole {
    role: string
}

export interface IError {
    detail: string
}

export enum EStatus {
    LOADING = 'loading',
    IDLE = 'idle',
    SUCCESS = 'success',
    ERROR = 'error'
}

export interface IPaginationResponse {
    total: number
    total_current_page: number;
    page: number
    size: number;
    pages: number;
    limit: number
    offset: number
}

export interface IPaginationRequest {
    limit?: number;
    offset?: number
}

export interface IApiErrorDetail {
    detail: {
        type: string;
        loc: string[],
        msg: string;
    }[]
}

export type ApiError = IApiErrorDetail | IError

export interface IChangePosition {
    id: string;
    position: number;
}

export interface IWindowData {
    version: 'ru' | 'ai',
    language: 'ru' | 'en'
}

export enum EFromRedirect {
    HISTORY = 'history'
}

export type TranslationType = (t: string) => string

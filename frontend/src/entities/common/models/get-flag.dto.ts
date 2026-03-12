export interface ICatalogFlag {
    flag_name: string;
    description: string;
    default_shown: boolean;
    default_view_count: number;
    is_active: boolean;
    created_at: string;
}

export interface IFlag {
    shown: boolean;
    view_count: number;
    last_update: string;
}

export type GetFlagCatalogResponseDto = ICatalogFlag[]

export interface IGetFlagUserResponseDto {
    user_id: string;
    created_at: string;
    updated_at: string
    flags: Record<EFlagSlug, IFlag>
}

export interface IUpdateFlagRequestDto {
    flag_name: string
    shown?: boolean
    increment_view?: boolean
    view_count?: number
}

export enum EFlagSlug {
    WELCOME = 'welcome',
    CHAT_BOT = 'chat_bot',
    ONBOARDING = 'onboarding',
}

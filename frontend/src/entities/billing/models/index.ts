import { IPaginationRequest, IPaginationResponse } from '@Common/types';
import { IMedia } from '@Entities/runs/models';

interface ITariff {
    tariff_name: ETariffName;
    tariff_full_name: string;
    description: string;
    additional_streams: number
    tariff_id: string
    can_buy_streams: boolean;
    is_free: boolean
}

export enum ETariffName {
    INDIVIDUAL = 'individual',
    CORPORATE = 'corporate',
}

interface ITariffLimitsWorkspace {
    name: string;
    created_at: string;
    tariff_start_date: string;
    status: string // TODO: поменять на enum
    tariff_expiration: string;
    workspace_max_concurrent_tasks_fact: number;
    next_reset_usage: string
}

interface ILimit {
    feature_name: string;
    feature_full_name: string;
    feature_full_simple: string;
    limit_value: number;
    current_usage: number;
}

export interface ITariffLimits {
    workspace: ITariffLimitsWorkspace
    tariff: ITariff
    limits: ILimit[]
    features: string[]
}

/** Тарифные планы */
export interface ITariffLimitPlan {
    tariff_id: string;
    total_price_in_month: number;
    tariff_name: ETariffName;
    tariff_full_name: string;
    description: string;
    discount: number;
    cur: string;
    buy_tariff_manual_only: boolean;
    can_buy_streams: boolean;
    cnt_months: number;
    price: number;
    period: string;
    best_value: boolean;
    visible: boolean;
    current_plan: boolean
    features: string[]
    tariff_limits: Omit<ILimit, 'current_usage'>[]
}

export interface IGetTariffLimitPlansPayload {
    cnt_months?: number
}

/** Просчитанные тарифы */
export interface ICalculatedTariffPlans {
    tariff_id: string;
    tariff_name: string;
    tariff_full_name?: string
    stream_count: number;
    monthly: {
        expiration_date: string;
        price: number;
        streams_price: number;
        total: number;
        total_before_discount: number;
        discount_percent: number;
        discount_amount: number;
        cur: string
        total_price_in_month?: number;
        total_price_in_month_without_streams?: number;
    }
    yearly: {
        expiration_date: string;
        price: number;
        total_price_in_month: number;
        streams_price: number;
        total: number;
        total_before_discount: number;
        total_price_in_month_without_streams: number;
        discount_percent: number;
        discount_amount: number;
        cur: string
    }
}

export interface IGetCalculatedPlansPayload {
    tariff_id: string;
    stream_count?: number;
    promocode?: string;
}

/** История платежей */
export enum EPaymentStatus {
    DRAFT = 'draft',
    SUBMITTED = 'submitted',
    EXECUTED = 'executed',
    FAILED = 'failed'
}

export interface IPaymentHistoryItem {
    transaction_id: string;
    /** TODO: status */
    status: EPaymentStatus
    invoice_number: string
    x_requests_id: string;
    invoice_id: string
    created_at: string;
    payment_dt: unknown | null;
    invoice_date: string;
    due_date: string;
    services: string;
    discount_amount: number;
    discount_percent: number;
    amount: number;
    cur: string;
    pdf: IMedia;
    payment_url: string;
    details: {
        name: string;
        inn: string;
        kpp: string;
        comment: string
    }

}

export interface IPaymentHistory extends IPaginationResponse {
    items: IPaymentHistoryItem[]
}

export interface IPaymentHistoryPayload extends IPaginationRequest {
    start_date?: string;
    end_date?: string;
    status?: string
}

/** Выставление счет юр лицам */
export interface ICreateCorporateInvoicePayload {
    tariff_id?: string;
    stream_count?: number;
    cnt_months?: number,
    promocode?: string;
    stream_only?: boolean
    name?: string;
    inn?: string;
    kpp?: string;
    comment?: string;
}

export interface ICreateCorporateInvoiceResponse {
    pdfUrl?: string;
    invoiceId?: string;
    incomingInvoiceUrl?: string

    errorId?: string;
    errorMessage?: string;
    errorCode?: string;
    errorDetails?: {
        message: string
    }
}

export interface IGetAdditionalStreamsParams {
    stream_count: number;
    promocode?: string
}

export interface IGetAdditionalStreamsResponse {
    workspace_id: string;
    tariff_expiration: string;
    current_date: string;
    cur: string;
    days_remaining: number;
    stream_count: number;
    stream_monthly_price: number;
    total_cost: number;
    can_buy_streams: boolean
}

export interface IContactUsPayload {
    username: string;
    email: string;
    question: string;
}

export interface ICreateIndividualPaymentPayload {
    tariff_id?: string;
    stream_count: number;
    cnt_months?: number;
    promocode?: string;
    stream_only?: boolean
}

export interface ICreateIndividualPaymentResponse {
    Success: boolean;
    ErrorCode: string;
    TerminalKey: string;
    Status: string;
    OrderId: string;
    Amount: number;
    PaymentURL: string
}

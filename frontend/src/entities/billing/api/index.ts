import { $api } from '@Common/api';
import {
    ICalculatedTariffPlans,
    IContactUsPayload,
    ICreateCorporateInvoicePayload,
    ICreateCorporateInvoiceResponse,
    ICreateIndividualPaymentPayload, ICreateIndividualPaymentResponse,
    IGetAdditionalStreamsParams,
    IGetAdditionalStreamsResponse,
    IGetCalculatedPlansPayload,
    IGetTariffLimitPlansPayload,
    IPaymentHistory,
    IPaymentHistoryPayload,
    ITariffLimitPlan,
    ITariffLimits
} from '@Entities/billing/models';

export class BillingApi {
    private static instance: BillingApi | null

    public static getInstance (): BillingApi {
        if (!this.instance) {
            this.instance = new BillingApi()

            return this.instance
        }

        return this.instance
    }

    async getTariffLimits (): Promise<ITariffLimits> {
        return (await $api.get('/billing/get_current_tariffs_limits_usage')).data
    }

    async getTariffPlans (params?: IGetTariffLimitPlansPayload): Promise<ITariffLimitPlan[]> {
        return (await $api.get(`/billing/get_list_tariffs_limits_plan`, { params })).data
    }

    async getCalculatedPlans (params?: IGetCalculatedPlansPayload): Promise<ICalculatedTariffPlans> {
        return (await $api.get('/billing/get_calculate_tariff_price', { params })).data
    }

    async getPaymentHistory (params?: IPaymentHistoryPayload): Promise<IPaymentHistory> {
        return (await $api.get(`/billing/get_user_transactions_billing`, { params })).data
    }

    async createCorporateInvoice (data: ICreateCorporateInvoicePayload): Promise<ICreateCorporateInvoiceResponse> {
        return (await $api.post(`/billing/create_corporate_invoice`, data)).data
    }

    async getCalculatedAdditionalStreams (params?: IGetAdditionalStreamsParams)
        : Promise<IGetAdditionalStreamsResponse> {
        return (await $api.get(`/billing/get_calculate_additional_stream`, { params })).data
    }

    async contactUs (data: IContactUsPayload): Promise<void> {
        return (await $api.post(`/billing/contact_us`, data)).data
    }

    async createIndividualPayment (data: ICreateIndividualPaymentPayload): Promise<ICreateIndividualPaymentResponse> {
        return (await $api.post(`/billing/create_individual_payment`, data)).data
    }
}

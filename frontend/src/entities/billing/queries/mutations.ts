import { BillingApi } from '@Entities/billing/api';
import {
    IContactUsPayload,
    ICreateCorporateInvoicePayload,
    ICreateIndividualPaymentPayload
} from '@Entities/billing/models';
import { billingQueries } from '@Entities/billing/queries/index.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const billingApi = BillingApi.getInstance()

export const useCreateCorporateInvoice = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: ICreateCorporateInvoicePayload) => billingApi.createCorporateInvoice(data),
        onSuccess: () => {
            queryClient.invalidateQueries(billingQueries.paymentHistory())
        }
    })
}

export const useContactUs = () => {
    return useMutation({
        mutationFn: (data: IContactUsPayload) => billingApi.contactUs(data)
    })
}

export const useCreateIndividualPayment = () => {
    return useMutation({
        mutationFn: (data: ICreateIndividualPaymentPayload) => billingApi.createIndividualPayment(data)
    })
}

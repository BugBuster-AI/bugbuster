import { BillingApi } from '@Entities/billing/api';
import {
    ICalculatedTariffPlans, IGetAdditionalStreamsParams, IGetAdditionalStreamsResponse,
    IGetCalculatedPlansPayload,
    IGetTariffLimitPlansPayload, IPaymentHistory, IPaymentHistoryPayload, ITariffLimits
} from '@Entities/billing/models';
import { billingQueryKeys } from '@Entities/billing/queries/query-keys.ts';
import { keepPreviousData, QueryObserverOptions, queryOptions } from '@tanstack/react-query';
import entries from 'lodash/entries';

const billingApi = BillingApi.getInstance()

export const billingQueries = {
    tariffLimits: (props?: Partial<QueryObserverOptions<ITariffLimits, Error>>) => queryOptions({
        queryKey: [billingQueryKeys.tariffLimits],
        queryFn: () => billingApi.getTariffLimits(),
        ...props
    }),
    tariffPlans: (params?: IGetTariffLimitPlansPayload) => queryOptions({
        queryKey: [billingQueryKeys.tariffPlans, ...entries(params)],
        queryFn: () => billingApi.getTariffPlans(params),
        placeholderData: keepPreviousData
    }),
    additionalStreams: (
        params?: IGetAdditionalStreamsParams,
        options?: Partial<QueryObserverOptions<IGetAdditionalStreamsResponse, Error>>
    ) => queryOptions({
        queryKey: [entries(params)],
        queryFn: () => billingApi.getCalculatedAdditionalStreams(params),
        ...options
    }),
    calculatedPlans: (
        params?: IGetCalculatedPlansPayload,
        options?: Partial<QueryObserverOptions<ICalculatedTariffPlans, Error>>
    ) => queryOptions({
        queryKey: [billingQueryKeys.calculatedPlans, ...entries(params)],
        queryFn: () => billingApi.getCalculatedPlans(params),
        ...options
    }),
    paymentHistory: (
        params?: IPaymentHistoryPayload,
        options?: Partial<QueryObserverOptions<IPaymentHistory, Error>>
    ) => queryOptions({
        queryKey: [billingQueryKeys.paymentHistory, ...entries(params)],
        queryFn: () => billingApi.getPaymentHistory(params),
        ...options
    })
}

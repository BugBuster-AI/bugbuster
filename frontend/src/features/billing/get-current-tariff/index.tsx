import { billingQueries } from '@Entities/billing/queries';
import { keepPreviousData, useQuery } from '@tanstack/react-query';

export const useCurrentTariff = () => {
    const { data, isLoading, error, isError } =
        useQuery(billingQueries.tariffLimits({ placeholderData: keepPreviousData }))

    return { data, loading: isLoading, error, isError }
}

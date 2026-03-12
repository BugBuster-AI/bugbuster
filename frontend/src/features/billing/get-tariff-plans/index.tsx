import { ITariffLimitPlan } from '@Entities/billing/models';
import { billingQueries } from '@Entities/billing/queries';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

export const useTariffPlans = () => {
    const [data, setData] = useState<ITariffLimitPlan[]>([])
    const [isLoading, setLoading] = useState(false)
    const queryClient = useQueryClient()

    const getData = async () => {
        setLoading(true)
        const asyncData = await queryClient.ensureQueryData(billingQueries.tariffPlans())

        setLoading(false)
        setData(asyncData)
    }

    useEffect(() => {
        getData()
    }, []);


    return { data, isLoading }
}

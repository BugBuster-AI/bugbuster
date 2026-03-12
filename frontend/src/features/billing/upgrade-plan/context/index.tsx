import { ICalculatedTariffPlans, IGetCalculatedPlansPayload, ITariffLimitPlan } from '@Entities/billing/models';
import { createContext, useContext } from 'react';

export type TCalculatedParams = Omit<IGetCalculatedPlansPayload, 'tariff_id'>

export interface IBuyStreamsContext {
    calculatedData?: ICalculatedTariffPlans
    currentTariffData?: ITariffLimitPlan
    isLoading: boolean;
    tariffName?: string
    isYearly?: boolean
    error?: string;

    totalPriceLoading?: boolean
    calculatedParams?: TCalculatedParams;
    setCalculatedParams: (data?: TCalculatedParams) => void
}

export const BuyStreamsContext = createContext<IBuyStreamsContext | undefined>(undefined)

export const useBuyStreamsContext = (): IBuyStreamsContext => {
    const context = useContext(BuyStreamsContext)

    if (!context) {
        throw new Error('useBuyStreamsContext must be used within a BuyStreamsProvider')
    }

    return context
}

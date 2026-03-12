import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { ETariffName, ITariffLimitPlan } from '@Entities/billing/models';
import { billingQueries } from '@Entities/billing/queries';
import { CorporatePlan } from '@Features/billing/upgrade-plan/components/Corporate';
import { IndividualPlan } from '@Features/billing/upgrade-plan/components/Individual';
import { BuyStreamsContext, TCalculatedParams } from '@Features/billing/upgrade-plan/context';
import { useTariffPlans } from '@Features/billing/upgrade-plan/hooks';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Button, Modal, Segmented } from 'antd';
import find from 'lodash/find';
import { ReactNode, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    tariffId: string
    isYearly?: boolean
    opened?: boolean
    noButton?: boolean
    tariffName?: string
    renderTrigger?: ({ onClick, open, tariffData, isLoading, error }: {
        onClick: () => void,
        open: boolean,
        tariffData?: ITariffLimitPlan[],
        isLoading?: boolean,
        error?: string
    }) => ReactNode
}

const initialParams = {
    stream_count: 0,
    promocode: ''
} as TCalculatedParams

export const UpgradePlan = ({ tariffId, noButton, opened = false, isYearly, renderTrigger, tariffName }: IProps) => {
    const { t } = useTranslation()
    const [open, setOpen] = useState(opened)
    const [currentPlan, setCurrentPlan] = useState<ETariffName>(ETariffName.INDIVIDUAL)
    const { data: tariffData, isLoading: tariffLoading } = useTariffPlans()
    const [calculatedParams, setCalculatedParams] = useState<TCalculatedParams | undefined>(initialParams)
    const currentTariffData = find(tariffData, { tariff_name: currentPlan })

    const {
        data,
        isLoading,
        isPlaceholderData,
        error
    } = useQuery(billingQueries.calculatedPlans({ tariff_id: tariffId, ...calculatedParams }, {
        enabled: !!currentTariffData?.tariff_id && open,
        placeholderData: keepPreviousData
    }))

    const options = [{
        label: t('buy_streams.individual'),
        value: ETariffName.INDIVIDUAL,
    }, {
        label: t('buy_streams.corporate'),
        value: ETariffName.CORPORATE
    }]

    const handleOpen = () => {
        setOpen(true)
    }

    const handleClose = () => {
        setOpen(false)
    }

    const errorMessage = getErrorMessage({ error, needConvertResponse: true })
    const memoizedValues = useMemo(() => {
        return {
            calculatedData: data,
            currentTariffData: currentTariffData,
            isLoading: tariffLoading || isLoading,
            tariffName,
            setCalculatedParams,
            totalPriceLoading: isPlaceholderData,
            calculatedParams,
            isYearly,
            error: getErrorMessage({ error, needConvertResponse: true })
        }
    }, [data, tariffData, isYearly, tariffName, tariffLoading, isLoading, isPlaceholderData, error, calculatedParams])

    useEffect(() => {
        setCalculatedParams(initialParams)
        setCurrentPlan(ETariffName.INDIVIDUAL)

    }, [open]);

    return (
        <BuyStreamsContext.Provider value={ memoizedValues }>

            {!noButton && (renderTrigger ? renderTrigger({
                error: errorMessage,
                isLoading: tariffLoading,
                onClick: handleOpen,
                tariffData,
                open
            }) : <Button onClick={ handleOpen } type={ 'primary' }>{t('common.upgrade')}</Button>)}
            <Modal
                cancelText={ t('buy_streams.paymentByCard') }
                footer={ null }
                okText={ t('buy_streams.ok') }
                onCancel={ handleClose }
                open={ open }
                title={ t('buy_streams.title') }
                centered
                destroyOnClose
            >
                <Segmented
                    className={ 'segmented-full-width' }
                    defaultValue={ ETariffName.INDIVIDUAL }
                    onChange={ setCurrentPlan }
                    options={ options }
                    value={ currentPlan }
                />
                {currentPlan === ETariffName.INDIVIDUAL && <IndividualPlan/>}
                {currentPlan === ETariffName.CORPORATE && <CorporatePlan/>}
            </Modal>
        </BuyStreamsContext.Provider>
    )
}

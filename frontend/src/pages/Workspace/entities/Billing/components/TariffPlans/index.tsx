import { TariffPlanCard } from '@Components/TariffPlanCard';
import { ITariffLimitPlan } from '@Entities/billing/models';
import { billingQueries } from '@Entities/billing/queries';
import { EWorkspaceStatus } from '@Entities/workspace/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { UpgradePlan } from '@Features/billing/upgrade-plan';
import { ContactUsModal } from '@Pages/Workspace/entities/Billing/components/ContactUsModal';
import { useQuery } from '@tanstack/react-query';
import { Button, Flex, Segmented, Spin, Typography } from 'antd';
import map from 'lodash/map';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const getCost = ({ cur, cost, month, t }: { cur: string, cost: number, month: number, t: (v: string) => string }) => {
    const isFree = cost === 0

    return `${isFree ? t('plans.free') : cost} ${isFree ? '' : cur} / ${month > 1 ? month : ''} ${t('common.month')}`
}


export const TariffPlans = () => {
    const { t } = useTranslation()
    const [currentPlan, setCurrentPlan] = useState(1)
    const workspace = useWorkspaceStore((state) => state.workspace)

    const { data, isLoading } = useQuery(billingQueries.tariffPlans({ cnt_months: currentPlan }))

    const items = [
        {
            label: t('plans.monthly'),
            value: 1
        },
        {
            label: t('plans.annual'),
            value: 12
        }
    ]

    const getButton = ({ current_plan, buy_tariff_manual_only, tariff_id, tariff_full_name }: ITariffLimitPlan) => {
        if (current_plan && workspace?.workspace_status !== EWorkspaceStatus.INACTIVE) {
            return <Button disabled>{t('plans.currentPlan')}</Button>
        }

        if (buy_tariff_manual_only) {
            return (
                <ContactUsModal
                    renderTrigger={ ({ onClick }) => (
                        <Button
                            color={ 'green' }
                            onClick={ onClick }
                            variant={ 'solid' }>
                            {t('plans.contactUs')}
                        </Button>
                    ) }
                />
            )
        }


        return <UpgradePlan
            isYearly={ currentPlan === 12 }
            tariffId={ tariff_id }
            tariffName={ tariff_full_name }
        />
    }

    return (
        <Flex style={ { width: '100%' } } vertical>
            <Typography.Title level={ 4 } style={ { marginBottom: 16 } }>{t('plans.title')}</Typography.Title>

            <Segmented
                onChange={ setCurrentPlan }
                options={ items }
                style={ { marginBottom: 16, width: 'fit-content' } }
            />

            <Spin spinning={ isLoading }>
                <Flex align={ 'stretch' } gap={ 16 } style={ { width: '100%' } } wrap>

                    {map(data, (item) => {
                        const cost = getCost({
                            cost: item.total_price_in_month,
                            cur: item.cur,
                            month: item.cnt_months,
                            t
                        })

                        if (!item.visible) return null

                        return (
                            <TariffPlanCard
                                key={ item.tariff_id }
                                Button={ getButton(item) }
                                cost={ !item.buy_tariff_manual_only ? cost : undefined }
                                features={ item.features }
                                isBest={ item.best_value }
                                subtitle={ item.description }
                                title={ item.tariff_full_name }
                            />
                        )
                    })}
                </Flex>
            </Spin>
        </Flex>
    )
}

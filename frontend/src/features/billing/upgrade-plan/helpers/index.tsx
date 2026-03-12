import { ICalculatedTariffPlans, ITariffLimitPlan } from '@Entities/billing/models';
import { ITeamPlanItem } from '@Features/billing/upgrade-plan/components/TeamPlan';
import { Flex } from 'antd';
import map from 'lodash/map';

export const getTooltipText = (plan?: ITariffLimitPlan, title?: string) => {
    if (!plan) {
        return null
    }

    return (
        <Flex vertical>
            <b>{title}</b>
            {plan?.description}
            <ul style={ { paddingLeft: 12, margin: 0 } }>
                {map(plan?.features, (item, index) => (
                    <li key={ `tooltip-li-item-${index}` }>
                        {item}
                    </li>
                ))}
            </ul>
        </Flex>
    )
}

export const getPlanItems = (t: (v: string) => string, data?: ICalculatedTariffPlans): ITeamPlanItem[] => {
    if (!data) return []
    const initialData = [data.monthly, data.yearly]

    return map(initialData, (item, index) => {
        return {
            untilDate: item.expiration_date,
            title: index === 0 ? t('plans.monthly') : t('plans.annual'),
            cost: item.price > 0 ?
                String(item?.total_price_in_month_without_streams || item.price) + ` ${item.cur}`
                : t('plans.free'),
            itemKey: String(index)
        } as ITeamPlanItem
    })
}

export const activePlanData = {
    '0': 'monthly',
    '1': 'yearly'
}

export const activePlanMonths = {
    '0': 1,
    '1': 12
}

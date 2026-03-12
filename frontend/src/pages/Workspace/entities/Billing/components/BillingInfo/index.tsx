import { ClockCircleOutlined } from '@ant-design/icons';
import { TextWithIcon } from '@Common/components';
import { useThemeToken } from '@Common/hooks';
import { billingQueries } from '@Entities/billing/queries';
import { ELimitType } from '@Entities/workspace/models';
import { BuyStreams } from '@Features/billing/buy-streams';
import { useQuery } from '@tanstack/react-query';
import { Flex, Spin } from 'antd';
import dayjs from 'dayjs';
import find from 'lodash/find';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BillingInfoCard } from './Card';

export const BillingInfo = () => {
    const { t } = useTranslation()
    const token = useThemeToken()
    const { data, isLoading } = useQuery(billingQueries.tariffLimits())
    const notFound = isLoading ? '' : t('common.not_found')
    const untilStreams = `${t('common.streams')} ${t('common.until')}`
    const tariffDateExpired = data?.workspace?.tariff_expiration
    // Конечная дата тарифа
    const tariffEndDate = data ? dayjs(tariffDateExpired).format('HH:mm DD.MM.YYYY') : ''

    //Дополнительные стримы тарифа
    const tariffAdditional = data?.tariff?.additional_streams
    const isTariffAdditional = Number(tariffAdditional) > 0

    const { recorderLimit, testCaseLimit } = useMemo(() => {
        return {
            testCaseLimit: find(data?.limits, { feature_name: ELimitType.START_GROUP_RUN }),
            recorderLimit: find(data?.limits, { feature_name: ELimitType.SAVE_HAPPY_PASS })
        }
    }, [data])

    // Если isTariffAdditional, то добавляем к строке streams
    const untilTariffDate = data
        ? isTariffAdditional ? `${tariffAdditional} ${untilStreams} ${dayjs(tariffDateExpired).format('DD.MM.YYYY')}`
            : ''
        : ''

    // Строка в streams
    const streamsString = data ?
        <>
            {data?.workspace?.workspace_max_concurrent_tasks_fact}
            {isTariffAdditional && (
                <TextWithIcon
                    icon={ <ClockCircleOutlined/> }

                    wrapperProps={ {
                        style: {
                            display: 'inline',
                            marginLeft: 16,
                        }
                    } }>
                    <span style={ { marginLeft: 4, color: token.colorTextDescription } }>{untilTariffDate}</span>
                </TextWithIcon>
            )}
        </>

        : notFound

    // Строка в test cases
    const testCaseLimitString = testCaseLimit
        ? `${testCaseLimit?.current_usage} / ${testCaseLimit?.limit_value}` : notFound

    // Строка в recorder entries
    const recorderLimitString = recorderLimit
        ? `${recorderLimit.current_usage} / ${recorderLimit.limit_value}` : notFound

    return (
        <Spin spinning={ isLoading }>
            <Flex gap={ 16 }>
                <BillingInfoCard title={ data?.tariff?.tariff_full_name || '' }>
                    <BillingInfoCard.Row content={ data?.workspace?.name } name={ t('workspace.index') }/>
                    <BillingInfoCard.Row
                        content={ tariffEndDate }
                        name={ t('workspace.billing.info.tariffEndDate') }/>
                    {data?.tariff?.can_buy_streams && <BuyStreams/>}
                </BillingInfoCard>
                <BillingInfoCard title={ t('workspace.billing.info.limits') }>
                    <BillingInfoCard.Row content={ streamsString } name={ t('workspace.billing.info.streams') }/>
                    <BillingInfoCard.Row
                        content={ testCaseLimitString }
                        name={ t('workspace.billing.info.testCases') }
                    />
                    <BillingInfoCard.Row
                        content={ recorderLimitString }
                        name={ t('workspace.billing.info.recorderEntries') }
                    />
                </BillingInfoCard>
            </Flex>
        </Spin>
    )
}

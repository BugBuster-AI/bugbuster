import { RocketOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { ELimitType } from '@Entities/workspace/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { BuyStreams } from '@Features/billing/buy-streams';
import { useCurrentTariff } from '@Features/billing/get-current-tariff';
import { Button, Flex, Skeleton, Typography } from 'antd';
import find from 'lodash/find';
import isNil from 'lodash/isNil';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

export const ShowTariffInfo = () => {
    const token = useThemeToken()
    const { data, loading, error } = useCurrentTariff()
    const { t } = useTranslation()
    const workspace = useWorkspaceStore((state) => state.workspace)

    const streamsLimit = find(data?.limits, { feature_name: ELimitType.MAX_TASKS })

    const getStreamsValue = (limit: typeof streamsLimit) => {
        if (isNil(limit)) {
            return ''
        }
        if (limit.limit_value === -1) {
            return t('common.unlimited')
        }

        return ` / ${limit.limit_value} ${t('common.streams')}`
    }

    const formattedTitle = data ? `${data?.tariff?.tariff_full_name}${getStreamsValue(streamsLimit)}` : ''

    const navigate = useNavigate()

    const handleUpgradeClick = () => {
        if (workspace) {
            navigate(PATHS.WORKSPACE.BILLING.ABSOLUTE)
        }
    }

    if (!!error) {
        return <Typography.Text type={ 'danger' }>Error</Typography.Text>
    }

    if (loading) {
        return <Skeleton.Node style={ { width: '100%', height: 140 } }/>
    }

    if (!data && !loading) {
        return null
    }

    return <Flex
        style={ {
            gap: 8,
            padding: 16,
            borderRadius: 8,
            background: token.colorBgBase,
            border: `1px solid ${token.colorBorderSecondary}`
        } }
        vertical
    >
        <Flex vertical>
            <Typography.Text>{formattedTitle}</Typography.Text>
            <Typography.Text type={ 'secondary' }>{data?.tariff?.description}</Typography.Text>
        </Flex>
        {data?.tariff && (
            data.tariff?.can_buy_streams ?
                <BuyStreams/>
                : <Button
                    icon={ <RocketOutlined/> }
                    onClick={ handleUpgradeClick }
                    type={ 'primary' }
                >
                    {t('common.upgrade')}
                </Button>
        )
        }

    </Flex>
}

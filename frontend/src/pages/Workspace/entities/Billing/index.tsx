import { BaseFlex } from '@Components/BaseLayout';
import { LayoutTitle } from '@Components/LayoutTitle';
import { EWorkspaceStatus } from '@Entities/workspace/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { UpgradePlan } from '@Features/billing/upgrade-plan';
import { BillingInfo } from '@Pages/Workspace/entities/Billing/components/BillingInfo';
import { PaymentHistory } from '@Pages/Workspace/entities/Billing/components/PaymentHistory';
import { TariffExpired } from '@Pages/Workspace/entities/Billing/components/TariffExpired';
import { TariffPlans } from '@Pages/Workspace/entities/Billing/components/TariffPlans';
import { Flex, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

export const BillingPage = () => {
    const workspace = useWorkspaceStore((state) => state.workspace)
    const { t } = useTranslation()
    const [searchParams] = useSearchParams()

    const redirectFromExpired = searchParams.get('expiredId')

    return (
        <Flex vertical>
            {!!redirectFromExpired && <UpgradePlan opened={ true } tariffId={ redirectFromExpired } noButton/>}
            <LayoutTitle
                title={ (
                    <Typography.Title level={ 3 } style={ { margin: 0, wordBreak: 'keep-all' } }>
                        {t('workspace.billing.title')}
                    </Typography.Title>
                ) }
            />

            {workspace?.workspace_status === EWorkspaceStatus.INACTIVE && (
                <BaseFlex style={ { paddingBlock: 0 } }>
                    <TariffExpired/>
                </BaseFlex>
            )
            }
            <BaseFlex>
                <BillingInfo/>
            </BaseFlex>

            <BaseFlex>
                <TariffPlans/>
            </BaseFlex>

            <BaseFlex>
                <PaymentHistory/>
            </BaseFlex>
        </Flex>
    )
}

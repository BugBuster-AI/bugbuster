import { ExclamationCircleOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { EWorkspaceStatus } from '@Entities/workspace/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { BuyStreams } from '@Features/billing/buy-streams';
import { useCurrentTariff } from '@Features/billing/get-current-tariff';
import { Button, Flex, Skeleton, Typography } from 'antd';
import { ComponentProps } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import styles from './HeaderUpgradeButton.module.scss'

interface IProps extends ComponentProps<typeof Button> {
}

const UpgradeButton = ({ children, ...props }: IProps) => {
    return <Button
        className={ styles.button }
        size={ 'small' }
        { ...props }
    >
        {children}
    </Button>
}

// Компонент - типа фича получается
export const HeaderUpgradeButton = () => {
    const { data, loading, isError } = useCurrentTariff()
    const { t } = useTranslation()
    const token = useThemeToken()
    const navigate = useNavigate()
    const workspace = useWorkspaceStore((state) => state.workspace)

    const handleUpgradeClick = () => {
        if (workspace) {
            navigate(PATHS.WORKSPACE.BILLING.ABSOLUTE)
        }
    }

    if (isError) {
        return null
    }

    if ((loading || !data || !workspace) && !isError) {
        return <Skeleton.Button/>
    }

    const isWorkspaceActive = workspace?.workspace_status === EWorkspaceStatus.ACTIVE

    const getWorkspaceAction = () => {
        if (isWorkspaceActive) {
            return data?.tariff?.can_buy_streams ? (
                <BuyStreams
                    renderButton={
                        ({ onClick }) => (
                            <UpgradeButton onClick={ onClick }>
                                {t('header.plans.buyStreams')}
                            </UpgradeButton>
                        )
                    }
                />
            ) : (
                <UpgradeButton onClick={ handleUpgradeClick }>
                    {t('common.upgrade')}
                </UpgradeButton>
            )
        }

        return (
            <UpgradeButton onClick={ handleUpgradeClick }>
                {t('common.upgrade')}
            </UpgradeButton>
        )
    }

    const borderColor = isWorkspaceActive ? token.colorPrimaryBorder : token.colorErrorBorder;
    const backgroundColor = isWorkspaceActive ? token.colorPrimaryBg : token.colorErrorBg;

    return (
        <Flex
            align={ 'center' }
            gap={ 4 }
            style={ {
                borderRadius: 32,
                padding: 8,
                background: backgroundColor,
                border: `1px solid ${borderColor}`
            } }>
            {!isWorkspaceActive && <ExclamationCircleOutlined style={ { color: token.colorError } }/>}
            <Typography.Text style={ { maxWidth: 220, paddingInline: 4 } } ellipsis>
                {t('header.plans.tariffName', { name: data?.tariff?.tariff_full_name })}
            </Typography.Text>
            {getWorkspaceAction()}
        </Flex>
    )
}

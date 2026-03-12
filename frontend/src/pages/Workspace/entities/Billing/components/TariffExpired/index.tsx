import { CloseCircleFilled } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

export const TariffExpired = () => {
    const token = useThemeToken()
    const { t } = useTranslation()


    return (
        <Flex
            align={ 'flex-start' }
            flex={ 1 }
            gap={ 16 }
            style={ {
                borderRadius: '8px',
                padding: '20px 24px',
                border: `1px solid ${token.colorErrorBorder}`,
                backgroundColor: token.colorErrorBg
            } }>
            <CloseCircleFilled style={ { fontSize: '24px', color: token.colorError } }/>

            <Flex gap={ 4 } vertical>
                <Typography.Text>{t('workspace.billing.expired.title')}</Typography.Text>
                <Typography.Text>{t('workspace.billing.expired.subtitle')}</Typography.Text>
            </Flex>
        </Flex>
    )
}

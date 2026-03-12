import { useThemeToken } from '@Common/hooks';
import { EPaymentStatus } from '@Entities/billing/models';
import { Tag } from 'antd';
import { useTranslation } from 'react-i18next';

export const usePaymentStatusColors = (status: EPaymentStatus) => {
    const token = useThemeToken()

    switch (status) {
        case EPaymentStatus.DRAFT:
            return {
                color: token.colorWarningText,
                background: token.colorWarningBg,
                border: `1px solid ${token.colorWarningBorder}`,
            }

        case EPaymentStatus.SUBMITTED:
            return {
                color: token.colorSuccessText,
                border: `1px solid ${token.colorSuccessBorder}`,
                backgroundColor: token.colorSuccessBg
            }
        case EPaymentStatus.EXECUTED:
            return {
                color: token.colorErrorText,
                border: `1px solid ${token.colorErrorBorder}`,
                backgroundColor: token.colorErrorBg
            }
        default :
            return {
                color: token.colorText,
                border: `1px solid ${token.colorBorder}`,
                backgroundColor: token.colorBgLayout
            }
    }
}

export const getColor = (status: EPaymentStatus) => {
    switch (status) {
        case EPaymentStatus.DRAFT:
            return 'gray'
        case EPaymentStatus.SUBMITTED:
            return 'orange'
        case EPaymentStatus.EXECUTED:
            return 'green'
        case EPaymentStatus.FAILED:
            return 'red'
        default:
            return 'default'

    }
}

export const PaymentStatus = ({ status }: { status?: EPaymentStatus }) => {
    const { t } = useTranslation()

    if (!status) return undefined

    const color = getColor(status)

    return <Tag color={ color }>
        {t(`paymentStatuses.${status}`)}
    </Tag>


}

import { DownloadOutlined } from '@ant-design/icons';
import { PaymentStatus } from '@Entities/billing/components/PaymentStatus';
import { IPaymentHistory, IPaymentHistoryItem } from '@Entities/billing/models';
import { Button, Flex, Table } from 'antd';
import { ColumnsType } from 'antd/es/table';
import { TableProps } from 'antd/lib';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';

interface IProps extends Omit<TableProps<IPaymentHistoryItem>, 'columns'> {
    data?: IPaymentHistory
}

export const PaymentHistoryTable = ({ data, ...props }: IProps) => {
    const { t } = useTranslation()

    const columns: ColumnsType<IPaymentHistoryItem> = [
        {
            title: t('paymentHistory.id'),
            width: 60,
            dataIndex: 'transaction_id',
            key: 'id',
            ellipsis: true,
        },
        {
            title: t('paymentHistory.date'),
            width: 160,
            key: 'date',
            dataIndex: 'created_date',
            render: (value) => dayjs(value).format('DD.MM.YYYY')
        },
        {
            title: t('paymentHistory.dueDate'),
            width: 160,
            key: 'due_date',
            dataIndex: 'due_date',
            render: (value) => dayjs(value).format('DD.MM.YYYY')
        },
        {
            title: t('paymentHistory.paymentDate'),
            width: 160,
            dataIndex: 'payment_dt',
            key: 'payment_dt',
            render: (value) => (value ? dayjs(value).format('DD.MM.YYYY') : '-')
        },
        {
            title: t('paymentHistory.status'),
            render: (value) => <PaymentStatus status={ value }/>,
            width: 160,
            dataIndex: 'status'
        },
        {
            title: t('paymentHistory.services'),
            width: 320,
            dataIndex: 'services',
            render: (value) => `${value}`
        },
        {
            title: t('paymentHistory.action'),
            width: 220,
            dataIndex: 'pdf',
            render: (_, data) => {
                const billUrl = data.pdf?.url
                const paymentUrl = data?.payment_url
                const handleOpenBill = () => {
                    if (!billUrl) return
                    window.open(billUrl, '_blank')
                }

                const handleOpenPayment = () => {
                    if (!paymentUrl) return
                    window.open(paymentUrl, '_blank')
                }

                return (
                    <Flex>
                        {!!billUrl && <Button
                            icon={ <DownloadOutlined/> }
                            onClick={ handleOpenBill }
                            type={ 'link' }
                        >
                            {t('paymentHistory.bill')}
                        </Button>}
                        {!!paymentUrl && <Button
                            icon={ <DownloadOutlined/> }
                            onClick={ handleOpenPayment }
                            type={ 'link' }
                        >
                            {t('paymentHistory.check')}
                        </Button>}
                    </Flex>
                )
            }
        }
    ]

    return <Table dataSource={ data?.items } size={ 'middle' } { ...props } columns={ columns }/>
}

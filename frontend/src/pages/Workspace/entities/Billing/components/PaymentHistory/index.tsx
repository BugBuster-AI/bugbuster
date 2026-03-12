import { PAGINATION } from '@Common/consts';
import { PaymentHistoryTable } from '@Entities/billing/components/PaymentHistoryTable';
import { billingQueries } from '@Entities/billing/queries';
import { useQuery } from '@tanstack/react-query';
import { Flex, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export const PaymentHistory = () => {
    const { t } = useTranslation()
    const [page, setPage] = useState(PAGINATION.PAGE)
    const [pageSize, setPageSize] = useState(PAGINATION.PAGE_SIZE)
    const { data, isLoading } = useQuery(billingQueries.paymentHistory({
        limit: pageSize,
        offset: (page - 1) * pageSize
    }))

    const handleChangePage = (page: number, pageSize: number) => {
        setPage(page)
        setPageSize(pageSize)
    }

    return (
        <Flex vertical>
            <Typography.Title level={ 4 } style={ { marginBottom: 16 } }>{t('plans.history')}</Typography.Title>
            <PaymentHistoryTable
                data={ data }
                loading={ isLoading }
                pagination={ {
                    pageSize,
                    total: data?.total,
                    showSizeChanger: true,
                    defaultCurrent: page,
                    onChange: handleChangePage,
                    pageSizeOptions: PAGINATION.PAGE_SIZE_OPTIONS
                } }
            />
        </Flex>
    )
}

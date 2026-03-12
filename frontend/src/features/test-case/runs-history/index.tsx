import { PAGINATION } from '@Common/consts';
import { RunHistoryCard } from '@Entities/runs/components';
import { runsQueries } from '@Entities/runs/queries';
import { useTestCaseStore } from '@Entities/test-case';
import { useQuery } from '@tanstack/react-query';
import { Empty, Flex, Pagination, Result, Skeleton, Spin } from 'antd';
import map from 'lodash/map';
import size from 'lodash/size';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export const TestCaseRunsHistory = () => {
    const [page, setPage] = useState(PAGINATION.PAGE)
    const [pageSize, setPageSize] = useState(PAGINATION.PAGE_SIZE)
    const currentCase = useTestCaseStore((state) => state.currentCase)
    const { t } = useTranslation()

    const offset = (page - 1) * pageSize
    const {
        data,
        isLoading,
        isError,
        isFetched,
        isFetching,
    } = useQuery(runsQueries.runList({
        case_id: currentCase?.case_id!!,
        limit: String(pageSize),
        offset: String(offset)
    }, !!currentCase?.case_id))

    const handlePaginationChange = (page: number, pageSize: number) => {
        setPage(page)
        setPageSize(pageSize)
    }

    if (isLoading) {
        return <Flex gap={ 16 } vertical>
            {map(Array.from({ length: 4 }), () => <Skeleton.Input block={ true }/>)}
        </Flex>
    }

    if (isError) {
        return <Result status={ '500' } title={ t('common.default_error') }/>
    }

    if (!isLoading && size(data?.items) === 0) {
        return <Empty description={ t('common.default_empty') }/>
    }

    return <Flex gap={ 8 } vertical>
        <Pagination
            current={ page }
            onChange={ handlePaginationChange }
            pageSize={ pageSize }
            pageSizeOptions={ PAGINATION.PAGE_SIZE_OPTIONS }
            size={ 'small' }
            total={ data?.total }
        />

        <Spin delay={ 200 } spinning={ isFetching && !isFetched }>
            <Flex gap={ 8 } vertical>
                {map(data?.items, (item, index) => (
                    <RunHistoryCard key={ `run-history-item-${index}` } { ...item }/>
                ))}
            </Flex>
        </Spin>
    </Flex>
}

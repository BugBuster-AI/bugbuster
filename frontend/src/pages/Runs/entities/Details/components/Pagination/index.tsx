import { PAGINATION } from '@Common/consts';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Flex, Pagination, Typography } from 'antd';
import head from 'lodash/head';
import size from 'lodash/size';
import { useEffect } from 'react';

export const GroupRunPagination = () => {
    const run = useGroupedRunStore((state) => state.data)
    const pagination = useGroupedRunStore((state) => state.pagination)
    const setPagination = useGroupedRunStore((state) => state.setPagination)

    const handleChange = (page: number, pageSize: number) => {
        setPagination({ page, pageSize })
    }


    useEffect(() => {
        return () => {
            setPagination({ page: PAGINATION.PAGE, pageSize: PAGINATION.PAGE_SIZE })
        }
    }, []);

    const suites = head(run?.items)

    if (!run) return null

    return (
        <Flex align={ 'center' } gap={ 16 }>
            <Pagination
                current={ pagination.page }
                defaultCurrent={ pagination.page }
                onChange={ handleChange }
                pageSize={ pagination.pageSize }
                pageSizeOptions={ PAGINATION.PAGE_SIZE_OPTIONS }
                total={ run.total }
                showSizeChanger
            />
            <Typography.Text>
                {`Total test runs: ${size(suites?.parallel)}`}
            </Typography.Text>
        </Flex>
    )
}

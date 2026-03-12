import { PAGINATION } from '@Common/consts';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { BaseFlex } from '@Components/BaseLayout';
import { LayoutTitle } from '@Components/LayoutTitle';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { LogsTable } from '@Entities/workspace/components/LogsTable';
import { workspaceQueries } from '@Entities/workspace/queries';
import { useQuery } from '@tanstack/react-query';
import { Flex, Result, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export const LogsPage = () => {
    const user = useAuthStore((state) => state.user)
    const { t } = useTranslation()
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(PAGINATION.PAGE_SIZE)

    const { data, isLoading, error } = useQuery({
        enabled: !!user,
        ...workspaceQueries.logs(user?.active_workspace_id!, {
            limit: String(pageSize),
            offset: String((page - 1) * pageSize),
        }),
    });

    if (!!error) {
        const errorMessage = getErrorMessage({
            error,
            needConvertResponse: true
        })

        return <Result status={ 'error' } title={ errorMessage }/>
    }

    const dataItems = data?.items

    const handlePaginationChange = (current: number, size: number) => {
        setPage(current);
        setPageSize(size);
    };

    return (

        <Flex vertical>
            <LayoutTitle
                title={ (
                    <Typography.Title level={ 3 } style={ { margin: 0, wordBreak: 'keep-all' } }>
                        {t('workspace.logs.title')}
                    </Typography.Title>
                ) }
            />
            <BaseFlex flex={ 1 } wrap={ 'wrap' } vertical>
                <LogsTable
                    data={ dataItems }
                    loading={ isLoading }
                    pagination={ {
                        pageSize,
                        current: page,
                        showSizeChanger: true,
                        pageSizeOptions: PAGINATION.PAGE_SIZE_OPTIONS,
                        total: data?.total || 0,
                        onChange: handlePaginationChange,
                    } }
                    size={ 'middle' }
                />
            </BaseFlex>
        </Flex>
    )
}

import { getErrorMessage } from '@Common/utils/getErrorMessage';
import { tokenQueries, useDeleteTokenMutation } from '@Entities/token';
import { TokensTable } from '@Entities/token/components';
import { EditToken } from '@Features/tokens/edit';
import { useQuery } from '@tanstack/react-query';
import { Flex, message } from 'antd';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

export const TokensList = () => {
    const { data, isLoading } = useQuery(tokenQueries.all());
    const { mutate: deleteToken, isPending } = useDeleteTokenMutation();
    const { t } = useTranslation()

    const handleDelete = (id: string) => {
        deleteToken(id, {
            onError: (error) => message.error(getErrorMessage({ error, needConvertResponse: true })),
            onSuccess: () => message.success(t('common.success'))
        })
    }

    const renderAction = useCallback((record) => (
        <Flex justify="end">
            <EditToken token={ record } />
        </Flex>
    ), [])

    return (
        <TokensTable
            data={ data }
            loading={ isLoading || isPending }
            onDelete={ (id) => handleDelete(id) }
            renderAction={ renderAction }
        />
    );
};

import { EditOutlined } from '@ant-design/icons';
import { getErrorMessage } from '@Common/utils/getErrorMessage';
import { useUpdateTokenMutation, useActivateTokenMutation, useDeactivateTokenMutation } from '@Entities/token';
import { IToken } from '@Entities/token/models';
import { Form, Switch, Typography, Space, message } from 'antd';
import { useTranslation } from 'react-i18next';
import { TokenModalButton } from '../components/TokenModalButton';

interface IProps {
    token: IToken;
}

export const EditToken = ({ token }: IProps) => {
    const { t } = useTranslation();
    const { mutateAsync: update, isPending: isUpdating } = useUpdateTokenMutation();
    const { mutateAsync: activate, isPending: isActivating } = useActivateTokenMutation();
    const { mutateAsync: deactivate, isPending: isDeactivating } = useDeactivateTokenMutation();

    const handleFinish = async (values: any) => {
        try {
            await update({
                token_id: token.token_id,
                name: values.name,
                expires_at: values.expires_at?.toISOString(),
            });
            message.success(t('common.success'))
        } catch(error: any) {
            const errorMessage = getErrorMessage({
                error,
                needConvertResponse: true
            })

            message.error(errorMessage)
            throw error
        }
    };

    const handleActiveChange = (checked: boolean) => {
        if (checked) {
            activate(token.token_id);
        } else {
            deactivate(token.token_id);
        }
    };

    const isPending = isUpdating || isActivating || isDeactivating;

    return (
        <TokenModalButton
            buttonProps={ { type: 'text' } }
            icon={ <EditOutlined /> }
            initialValues={ token }
            isLoading={ isPending }
            onFinish={ handleFinish }
            title={ t('workspace.api_keys.edit_title', 'Edit API Key') }
        >
            <Form.Item label={ t('workspace.api_keys.modal.status', 'Status') }>
                <Space>
                    <Switch
                        checked={ token.is_active }
                        loading={ isActivating || isDeactivating }
                        onChange={ handleActiveChange }
                    />
                    <Typography.Text>
                        {token.is_active ? t('unique_key_active', 'Active') : t('unique_key_inactive', 'Inactive')}
                    </Typography.Text>
                </Space>
            </Form.Item>
        </TokenModalButton>
    );
};

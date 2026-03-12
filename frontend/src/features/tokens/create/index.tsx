import { CopyOutlined, PlusOutlined } from '@ant-design/icons';
import { getErrorMessage } from '@Common/utils/getErrorMessage';
import { useCreateTokenMutation } from '@Entities/token';
import { IToken } from '@Entities/token/models';
import { TokenModalButton } from '@Features/tokens/components/TokenModalButton';
import { Button, Input, Modal, Typography, message } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export const CreateToken = () => {
    const { t } = useTranslation();
    const { mutateAsync, isPending } = useCreateTokenMutation();
    const [createdToken, setCreatedToken] = useState<IToken | null>(null);

    const handleFinish = async (values: any) => {
        try {
            const result = await mutateAsync({
                name: values.name,
                expires_at: values.expires_at?.toISOString(),
            });

            setCreatedToken(result);
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

    const handleCopy = () => {
        if (createdToken?.token) {
            navigator.clipboard.writeText(createdToken.token);
            message.success(t('workspace.api_keys.copy_success', 'Token copied to clipboard'));
        }
    };

    const handleCloseSuccess = () => {
        setCreatedToken(null);
    };

    return (
        <>
            <TokenModalButton
                isLoading={ isPending }
                onFinish={ handleFinish }
                renderButton={ ({ onClick }) => (
                    <Button
                        icon={ <PlusOutlined /> }
                        onClick={ onClick }
                        type="primary"
                    >
                        {t('workspace.api_keys.create_button')}
                    </Button>
                ) }
                title={ t('workspace.api_keys.create_title') }
            />
            <Modal
                centered={ true }
                footer={ [
                    <Button key="close" onClick={ handleCloseSuccess } type="primary">
                        {t('workspace.api_keys.modal.close', 'Close')}
                    </Button>
                ] }
                onCancel={ handleCloseSuccess }
                open={ !!createdToken }
                title={ t('workspace.api_keys.success_title', 'API Key Created') }
                destroyOnClose
            >
                <Typography.Paragraph>
                    {t('workspace.api_keys.success_message')}
                </Typography.Paragraph>
                <Input.Group compact>
                    <Input
                        style={ { width: 'calc(100% - 32px)' } }
                        value={ createdToken?.token }
                        readOnly
                    />
                    <Button
                        icon={ <CopyOutlined /> }
                        onClick={ () => handleCopy() }
                    />
                </Input.Group>
            </Modal>
        </>
    );
};

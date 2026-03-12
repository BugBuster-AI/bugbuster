import { IModalRef, ModalButton } from '@Components/ModalButton';
import { IToken } from '@Entities/token/models';
import { Form, Input, DatePicker } from 'antd';
import dayjs from 'dayjs';
import { ReactNode, useRef, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    onFinish: (values: any) => Promise<void>;
    isLoading?: boolean;
    initialValues?: Partial<IToken>;
    title: string;
    icon?: ReactNode;
    renderButton?: (props: { onClick: () => void }) => ReactNode;
    buttonProps?: any; // Pass through props
    children?: ReactNode;
    open?: boolean; // Add open prop to track modal state change if passed from parent or internal
}

export const TokenModalButton = ({
    onFinish,
    isLoading,
    initialValues,
    title,
    icon,
    renderButton,
    buttonProps,
    children
}: IProps) => {
    const { t } = useTranslation();
    const [form] = Form.useForm();
    const modalRef = useRef<IModalRef>(null);
    const [hasInitialValuesBeenSet, setHasInitialValuesBeenSet] = useState(false);

    const handleOk = () => {
        form.submit();
    };

    const onSubmit = async (values: any) => {
        try {
            await onFinish(values);
            modalRef.current?.close();
            form.resetFields()
        } catch (error) {
            console.error(error);
        }
    };

    const initialFormData = initialValues ? {
        name: initialValues.name,
        expires_at: initialValues.expires_at ? dayjs(initialValues.expires_at) : undefined
    } : undefined;

    useEffect(() => {
        if (initialFormData && !hasInitialValuesBeenSet) {
            form.setFieldsValue(initialFormData);
            setHasInitialValuesBeenSet(true);
        }
    }, [initialFormData, form, hasInitialValuesBeenSet]);

    return (
        <ModalButton
            ref={ modalRef }
            buttonProps={ buttonProps }
            icon={ icon }
            modalProps={ {
                onOk: handleOk,
                okButtonProps: { loading: isLoading },
                title: title,
                destroyOnClose: true,
                onClose: () => {
                    form.resetFields();
                    setHasInitialValuesBeenSet(false);
                },
                centered: true,
                okText: t('workspace.api_keys.modal.ok', 'Save'),
                cancelText: t('workspace.api_keys.modal.cancel', 'Cancel')
            } }
            renderButton={ renderButton }
        >
            <Form
                form={ form }
                initialValues={ initialFormData }
                layout="vertical"
                onFinish={ onSubmit }
                clearOnDestroy
            >
                <Form.Item
                    label={ t('workspace.api_keys.modal.name', 'Name') }
                    name="name"
                >
                    <Input placeholder={ t('workspace.api_keys.modal.name_placeholder', 'Token Name') } />
                </Form.Item>
                <Form.Item
                    label={ t('workspace.api_keys.modal.expires_at', 'Expires at') }
                    name="expires_at"
                >
                    <DatePicker style={ { width: '100%' } } />
                </Form.Item>
                {children}
            </Form>
        </ModalButton>
    );
};

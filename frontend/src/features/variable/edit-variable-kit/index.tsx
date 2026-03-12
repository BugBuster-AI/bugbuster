import { EditOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { compactObj } from '@Common/utils/compactObj.ts';
import { IVariableKitForm, VariableKitForm } from '@Entities/variable/components/KitForm';
import { IUpdateVariableKitRequest, IVariableKit } from '@Entities/variable/models';
import { useUpdateVariableKit, variableQueries } from '@Entities/variable/queries';
import { useQuery } from '@tanstack/react-query';
import { Button, ButtonProps, Form, Modal } from 'antd';
import { ReactNode, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

const httpFields = {
    variables_kit_description: 'description',
    variables_kit_name: 'name'
} as Record<keyof IUpdateVariableKitRequest, keyof IVariableKitForm>


const getLocalFormValues = (data?: IVariableKit): Partial<IVariableKitForm> => {
    if (!data) {
        return {}
    }

    return {
        description: data.variables_kit_description,
        name: data.variables_kit_name,
    }
}

interface IProps {
    data: IVariableKit
    renderButton?: ({ onClick }: { onClick: () => void }) => ReactNode
    buttonProps?: ButtonProps
}

export const EditVariableKit = ({ data: localData, renderButton, buttonProps }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage' })
    const { mutateAsync, isPending } = useUpdateVariableKit()
    const [form] = Form.useForm<IVariableKitForm>()
    const [open, setOpen] = useState(false)
    const { data: httpData } = useQuery(variableQueries.kitItem({ variables_kit_id: localData.variables_kit_id }, {
        enabled: open,
        placeholderData: localData
    }))

    const handleOpenModal = () => {
        setOpen(true)
    }

    const handleCloseModal = () => {
        setOpen(false)
    }

    const handleSubmit = async () => {
        const formData = form.getFieldsValue()

        try {
            await form.validateFields()
            const data = compactObj({
                variables_kit_description: formData.description,
                variables_kit_name: formData.name,
                variables_kit_id: localData.variables_kit_id,
            })

            await asyncHandler(mutateAsync.bind(null, data), {
                successMessage: t('update.success'),
                formValidate: {
                    formInstance: form,
                    transformFields: httpFields
                },
                onSuccess: () => {
                    form.resetFields()
                    handleCloseModal()
                }
            })
        } catch {
            return
        }
    }

    const initialData = useMemo(() => getLocalFormValues(httpData), [localData, httpData])

    return (
        <>
            {renderButton ? renderButton({ onClick: handleOpenModal })
                : <Button
                    icon={ <EditOutlined/> }
                    onClick={ handleOpenModal }
                    type={ 'text' }
                    variant={ 'text' }
                    { ...buttonProps }
                />}
            <Modal
                cancelText={ t('update.cancel') }
                okButtonProps={ {
                    loading: isPending
                } }
                okText={ t('update.ok') }
                onCancel={ handleCloseModal }
                onOk={ handleSubmit }
                open={ open }
                title={ t('update.title') }
                centered
                closable
                destroyOnClose
                maskClosable
            >
                <VariableKitForm form={ form } initialValues={ initialData }/>
            </Modal>
        </>
    )
}

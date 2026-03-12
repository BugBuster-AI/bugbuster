import { PlusOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { compactObj } from '@Common/utils/compactObj.ts';
import { useProjectStore } from '@Entities/project/store';
import { IVariableKitForm, VariableKitForm } from '@Entities/variable/components/KitForm';
import { ICreateVariableKitRequest } from '@Entities/variable/models';
import { useCreateVariableKit } from '@Entities/variable/queries';
import { Button, Form, Modal } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const httpFields = {
    variables_kit_description: 'description',
    variables_kit_name: 'name'
} as Record<keyof ICreateVariableKitRequest, keyof IVariableKitForm>

export const CreateVariableKit = () => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage' })
    const { mutateAsync, isPending } = useCreateVariableKit()
    const [form] = Form.useForm<IVariableKitForm>()
    const [open, setOpen] = useState(false)
    const project = useProjectStore((state) => state.currentProject)!
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
                project_id: project.project_id,
            })

            await asyncHandler(mutateAsync.bind(null, data), {
                successMessage: t('create.success'),
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

    return (
        <>
            <Button icon={ <PlusOutlined/> } onClick={ handleOpenModal } type={ 'primary' }>
                {t('add')}
            </Button>
            <Modal
                cancelText={ t('create.cancel') }
                okButtonProps={ {
                    loading: isPending
                } }
                okText={ t('create.ok') }
                onCancel={ handleCloseModal }
                onOk={ handleSubmit }
                open={ open }
                title={ t('create.title') }
                centered
                closable
                destroyOnClose
                maskClosable
            >
                <VariableKitForm form={ form }/>
            </Modal>
        </>
    )
}

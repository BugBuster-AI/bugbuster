import { PlusOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { IVariableForm, VariableForm } from '@Entities/variable/components/VariableForm';
import { toHttpData } from '@Entities/variable/components/VariableForm/adapters';
import { ICreateVariableRequest } from '@Entities/variable/models/create-variable.dto.ts';
import { VariableType } from '@Entities/variable/models/types';
import { useCreateVariable } from '@Entities/variable/queries';
import { Button, Checkbox, CheckboxProps, Form, Modal } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

const httpFields = {
    variable_name: 'variable_name',
} as Record<keyof ICreateVariableRequest, keyof IVariableForm>


export const CreateVariable = () => {
    const { t } = useTranslation('', { keyPrefix: 'variablesPage.details' })
    const { mutateAsync, isPending } = useCreateVariable()
    const [form] = Form.useForm<IVariableForm>()
    const { variableKitId } = useParams()
    const [needCreateAnother, setNeedCreateAnother] = useState(false)
    const [open, setOpen] = useState(false)

    const handleOpenModal = () => {
        setOpen(true)
    }

    const handleCloseModal = () => {
        setOpen(false)
        // form.resetFields()
    }

    const handleSubmit = async () => {
        const formData = form.getFieldsValue()

        try {
            await form.validateFields()

            const httpData = toHttpData(formData);
            const data = {
                ...httpData,
                variables_kit_id: variableKitId!,
            } as ICreateVariableRequest;

            await asyncHandler(mutateAsync.bind(null, data), {
                successMessage: t('create.success'),
                formValidate: {
                    formInstance: form,
                    transformFields: httpFields
                },
                onSuccess: () => {
                    form.resetFields()
                    if (needCreateAnother) {
                        return
                    }
                    handleCloseModal()
                }
            })
        } catch {
    
            return
        }
    }

    const handleChangeCreateAnother: CheckboxProps['onChange'] = (e) => {
        setNeedCreateAnother(e.target.checked)
    }

    return (
        <>
            <Button icon={ <PlusOutlined/> } onClick={ handleOpenModal } type={ 'primary' }>
                {t('add')}
            </Button>
            <Modal
                cancelText={ t('create.cancel') }
                footer={ (originNode) => {
                    return (
                        <>
                            <Checkbox onChange={ handleChangeCreateAnother }>
                                {t('create.createAnother')}
                            </Checkbox>
                            {originNode}
                        </>
                    )
                } }
                okButtonProps={ {
                    loading: isPending,
                } }
                okText={ t('create.ok') }
                onCancel={ handleCloseModal }
                onOk={ handleSubmit }
                open={ open }
                title={ t('create.title') }
                wrapClassName="no-scrollbar"
                centered
                closable
                destroyOnClose
                maskClosable
            >
                <VariableForm
                    form={ form }
                    initialValues={ {
                        variables_kit_id: variableKitId,
                        variable_config: {
                            type: VariableType.simple
                        }
                    } }
                />
            </Modal>
        </>
    )
}

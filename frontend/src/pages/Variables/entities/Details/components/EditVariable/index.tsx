import { EditOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { IVariableForm, VariableForm } from '@Entities/variable/components/VariableForm';
import { toHttpData } from '@Entities/variable/components/VariableForm/adapters';
import { IVariable } from '@Entities/variable/models';
import { IUpdateVariableRequest } from '@Entities/variable/models/update-variable.dto.ts';
import { useUpdateVariable, variableQueries, variableQueryKeys } from '@Entities/variable/queries';
import { getLocalFormValues } from '@Pages/Variables/entities/Details/components/EditVariable/helper.ts';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Form, Modal, Spin } from 'antd';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';


interface IProps {
    data: IVariable
}

export const UpdateVariable = ({ data: localData }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage.details' })
    const { mutateAsync, isPending } = useUpdateVariable()
    const [form] = Form.useForm<IVariableForm>()
    const [open, setOpen] = useState(false)
    const queryClient = useQueryClient()
    const { data: httpData, isLoading } = useQuery(variableQueries.variableItem(
        { variable_details_id: localData.variable_details_id },
        { enabled: !!localData.variable_details_id && open, placeholderData: undefined, gcTime: 0 }))

    const handleOpenModal = () => {
        setOpen(true)
        // form.resetFields()
    }

    const handleCloseModal = () => {
        // form.resetFields()
        queryClient.removeQueries({ queryKey: [variableQueryKeys.variableItem] })

        setTimeout(() => {
            setOpen(false)
        }, 0)
    }

    const handleSubmit = async () => {
        const formData = form.getFieldsValue()
        
        try {
            await form.validateFields()

            const httpData = toHttpData(formData);
            const data = {
                ...httpData,
                variable_details_id: localData.variable_details_id,
            } as IUpdateVariableRequest;

            await asyncHandler(mutateAsync.bind(null, data), {
                successMessage: t('update.success'),
                /*
                 * formValidate: {
                 *     formInstance: form,
                 *     transformFields: httpFields
                 * },
                 */
                onSuccess: () => {
                    form.resetFields()
                    handleCloseModal()
                }
            })
        } catch {
            return
        }
    }

    const initialValues = useMemo(() => (getLocalFormValues(httpData)), [localData, httpData, open]);

    return (
        <>
            <Button
                icon={ <EditOutlined/> }
                onClick={ handleOpenModal }
                type={ 'text' }
                variant={ 'text' }
            />
            <Modal
                cancelText={ t('update.cancel') }
                okButtonProps={ {
                    loading: isPending,
                } }
                okText={ t('update.ok') }

                onCancel={ handleCloseModal }
                onOk={ handleSubmit }
                open={ open }
                title={ t('update.title') }
                wrapClassName="no-scrollbar"
                centered
                closable
                destroyOnClose
                maskClosable
            >
                <Spin spinning={ isLoading }>
                    <VariableForm form={ form } initialValues={ initialValues } isLoading={ isLoading }/>
                </Spin>
            </Modal>
        </>
    )
}

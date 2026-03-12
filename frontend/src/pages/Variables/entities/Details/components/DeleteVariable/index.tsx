import { DeleteOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { IVariable } from '@Entities/variable/models';
import { useDeleteVariable } from '@Entities/variable/queries';
import { Button, ButtonProps, Modal } from 'antd';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

interface IProps {
    data: IVariable
    buttonProps?: ButtonProps
}

export const DeleteVariable = ({ data: variable, buttonProps }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage.details' })
    const { variableKitId } = useParams()
    const { mutateAsync, isPending } = useDeleteVariable(variableKitId || variable.variables_kit_id)
    const handleDelete = async () => {
        Modal.confirm({
            centered: true,
            title: t('delete.title'),
            okText: t('delete.ok'),
            closable: true,
            maskClosable: true,
            icon: null,
            okButtonProps: {
                variant: 'solid',
                color: 'danger',
                loading: isPending
            },
            cancelText: t('delete.cancel'),
            content: t('delete.content', { name: variable.variable_name }),
            onOk: async () => {
                await asyncHandler(mutateAsync.bind(null, { variable_details_id: variable.variable_details_id }))
            }
        })

    }

    return (
        <Button
            icon={ <DeleteOutlined/> }
            onClick={ handleDelete }
            type={ 'text' }
            variant={ 'text' }
            { ...buttonProps }
        />
    )

}

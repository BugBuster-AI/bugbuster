import { DeleteOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { useProjectStore } from '@Entities/project/store';
import { IVariableKit } from '@Entities/variable/models';
import { useDeleteVariableKit, variableQueries } from '@Entities/variable/queries';
import { useQuery } from '@tanstack/react-query';
import { Button, ButtonProps, Modal } from 'antd';
import { ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    data: IVariableKit
    renderButton?: ({ onClick }: { onClick: () => void }) => ReactNode
    buttonProps?: ButtonProps
    onSuccess?: () => void
}

export const DeleteVariableKit = ({ renderButton, onSuccess, data: kit, buttonProps }: IProps) => {
    const project = useProjectStore((state) => state.currentProject)
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage' })
    const { t: common } = useTranslation()
    const [open, setOpen] = useState(false)

    const {
        data,
    } = useQuery(variableQueries.variableList({ variables_kit_id: kit.variables_kit_id! }, { enabled: !!kit && open }),)

    const getText = () => {
        let text = common('common.variables')
        const count = data?.variables_count
        const baseText = t('delete.content', { name: kit.variables_kit_name, count })

        if (count === 1) {
            text = common('common.variable')
        }

        return `${baseText} ${text}?`
    }

    const { mutateAsync, isPending } = useDeleteVariableKit(project?.project_id!)
    const handleDelete = async () => {
        Modal.confirm({
            open,
            afterOpenChange: (isOpen) => setOpen(isOpen),
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
            content: getText(),
            onOk: async () => {
                await asyncHandler(mutateAsync.bind(null,
                    { variables_kit_id: kit.variables_kit_id },
                    { onSuccess }
                ))
            }
        })

    }

    if (renderButton) {
        return renderButton({ onClick: handleDelete })
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

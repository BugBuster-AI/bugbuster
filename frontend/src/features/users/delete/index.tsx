import { DeleteOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { IUserListItem } from '@Entities/users/models';
import { useDeleteUser } from '@Entities/users/queries/mutations.ts';
import { useTranslation } from 'react-i18next';

export const DeleteUser = ({ first_name, last_name, role, email }: IUserListItem) => {
    const { t } = useTranslation()
    const { mutateAsync, isPending } = useDeleteUser()

    const name = (first_name || last_name) ? `${first_name || ''} ${last_name || ''}` : ''
    const workspace = 'workspace-test'

    const handleClick = async () => {
        if (email) {
            await asyncHandler(mutateAsync.bind(null, email))
        }
    }

    return (
        <ConfirmButton
            buttonProps={ { variant: 'filled', type: 'text' } }
            icon={ <DeleteOutlined/> }
            modalProps={ {
                okButtonProps: {
                    loading: isPending
                },
                title: t('users.delete_confirm.title', { name }),
                centered: true,
                destroyOnClose: true,
                onOk: handleClick,
                okText: t('users.delete_confirm.remove'),
                cancelText: t('users.delete_confirm.cancel')
            } }
            closeAfterOk
        >
            <div>{t('users.delete_confirm.body', { name, workspace, role })}</div>
        </ConfirmButton>
    )
}

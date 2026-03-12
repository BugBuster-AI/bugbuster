import { EditOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { IModalRef, ModalButton } from '@Components/ModalButton';
import { ProfileForm } from '@Entities/users/components/ProfileForm';
import { IUserListItem } from '@Entities/users/models';
import { useEditUser } from '@Entities/users/queries/mutations.ts';
import { Form } from 'antd';
import map from 'lodash/map';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    user: IUserListItem
}

export const EditUser = ({ user }: IProps) => {
    const { t } = useTranslation()
    const { mutateAsync, isPending } = useEditUser()
    const [form] = Form.useForm()

    const modalRef = useRef<IModalRef>(null)

    const handleOk = () => {
        form.submit()
    }

    const onSubmit = async () => {
        const data = form.getFieldsValue()

        await asyncHandler(mutateAsync.bind(null, data), {
            onSuccess: () => modalRef.current?.close()
        })
    }

    return (
        <ModalButton
            ref={ modalRef }
            buttonProps={ { variant: 'filled', type: 'text' } }
            icon={ <EditOutlined/> }
            modalProps={ {
                onOk: handleOk,
                okButtonProps: {
                    loading: isPending
                },
                width: 720,
                title: t('users.invite_modal.profile_title'),
                centered: true,
                onClose: () => form.resetFields(),
                destroyOnClose: true
            } }
        >
            <ProfileForm
                emailDisabled={ true }
                form={ form }
                initialValues={ {
                    email: user.email,
                    role: user.role,
                    first_name: user?.first_name,
                    last_name: user?.last_name,
                    project_ids: map(user?.projects, (item) => item.project_id),
                    role_title: user?.role_title
                } }
                onFinish={ onSubmit }
            />
        </ModalButton>
    )
}

import { asyncHandler } from '@Common/utils';
import { IModalRef, ModalButton } from '@Components/ModalButton';
import { ProfileForm } from '@Entities/users/components/ProfileForm';
import { IInviteUserDto } from '@Entities/users/models/invite-user.dto.ts';
import { useInviteUser } from '@Entities/users/queries/mutations.ts';
import { ELimitType } from '@Entities/workspace/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { Button, Form, Tooltip } from 'antd';
import find from 'lodash/find';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';

export const InviteUser = () => {
    const { t } = useTranslation()
    const [form] = Form.useForm()
    const { mutateAsync, isPending } = useInviteUser()
    const modalRef = useRef<IModalRef>(null)
    const limits = useWorkspaceStore((state) => state.limits)
    const currentLimit = find(limits, { feature_name: ELimitType.INVITE_USER })

    const handleOk = () => {
        form.submit()
    }

    const onSubmit = async () => {
        const data = form.getFieldsValue()

        const formData = {
            ...data,
            language: 'ru'
        } as IInviteUserDto

        await asyncHandler(mutateAsync.bind(null, formData), {
            onSuccess: () => modalRef.current?.close()
        })
    }

    const isLimit = currentLimit?.remaining === 0 || !currentLimit

    return (
        <ModalButton
            ref={ modalRef }
            buttonProps={ { variant: 'filled', type: 'text' } }
            modalProps={ {
                width: 720,
                title: t('users.invite_modal.title'),
                centered: true,
                destroyOnClose: true,
                onOk: handleOk,
                okButtonProps: {
                    loading: isPending
                },
                okText: t('users.invite_modal.ok'),
                cancelText: t('users.invite_modal.cancel')
            } }
            renderButton={
                ({ onClick }) => (
                    <Tooltip title={ isLimit ? t('users.invite_limit') : '' }>
                        <Button disabled={ isLimit } onClick={ onClick } type={ 'primary' }>
                            {t('users.invite')}
                        </Button>
                    </Tooltip>
                )
            }
        >
            <ProfileForm clearOnDestroy={ true } form={ form } onFinish={ onSubmit }/>
        </ModalButton>
    )
}

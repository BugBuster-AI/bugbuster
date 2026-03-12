import { EditOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { asyncHandler } from '@Common/utils';
import { IModalRef, ModalButton } from '@Components/ModalButton';
import { useChangeWorkspaceName } from '@Entities/workspace/queries/mutations.ts';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { Flex, Form, Input, Typography } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

export const EditWorkspaceName = () => {
    const { t } = useTranslation()
    const [name, setName] = useState<string | undefined>(undefined)
    const { workspaceId } = useParams()
    const { mutateAsync, isPending } = useChangeWorkspaceName(workspaceId!)
    const workspace = useWorkspaceStore((state) => state.workspace)
    const ref = useRef<IModalRef>(null)
    const token = useThemeToken()

    useEffect(() => {
        if (workspace && !name) {
            setName(workspace?.workspace_name)
        }
    }, [workspace]);

    const onSubmit = async () => {
        if (name) {
            await asyncHandler(mutateAsync.bind(null, name), {
                onSuccess: () => ref.current?.close()
            })
        }
    }

    return (
        <ModalButton
            ref={ ref }
            buttonProps={ {
                variant: 'filled',
                type: 'text'
            } }
            icon={ <EditOutlined/> }
            modalProps={ {
                centered: true,
                okButtonProps: {
                    loading: isPending
                },
                onClose: () => setName(workspace?.workspace_name),
                destroyOnClose: true,
                onOk: onSubmit,
                okText: t('users.edit_name_modal.save'),
                cancelText: t('users.edit_name_modal.cancel'),
                title: t('users.edit_name_modal.title')
            } }
            renderContent={
                <Flex
                    vertical
                >
                    <Form.Item
                        extra={ !name && <Typography.Text
                            style={ { color: token.colorErrorText } }>{t('errors.input.required')}</Typography.Text> }
                        initialValue={ workspace?.workspace_name }
                        label={ t('users.edit_name_modal.workspace_name') }
                        layout={ 'vertical' }
                        style={ { marginTop: '16px' } }
                    >
                        <Input

                            onChange={ (e) => setName(e.target.value) }
                            placeholder={ t('users.edit_name_modal.placeholder') }
                            value={ name }
                        />
                    </Form.Item>
                </Flex>
            }
        />
    )
}

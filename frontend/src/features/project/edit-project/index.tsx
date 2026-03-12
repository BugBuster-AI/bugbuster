import { EditOutlined } from '@ant-design/icons';
import { asyncHandler } from '@Common/utils';
import { MaxParallelsInput } from '@Components/MaxParallelsInput';
import { ModalButton } from '@Components/ModalButton';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { ProjectForm } from '@Entities/project/components/ProjectForm';
import { ITableProjectListItem } from '@Entities/project/components/Table';
import { projectQueries } from '@Entities/project/queries';
import { useUpdateProject } from '@Entities/project/queries/mutations';
import { streamQueryKeys } from '@Entities/stream/queries/query-keys.ts';
import { EUserRole } from '@Entities/users/models';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Form } from 'antd';
import { ReactElement, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    initialValues: Pick<ITableProjectListItem, 'name' | 'description' | 'project_id' | 'max_streams' | 'parallel_exec'>
}

export const EditProject = ({ initialValues }: IProps): ReactElement => {
    const { project_id, name } = initialValues || {};
    const [open, setOpen] = useState(false)
    const { mutateAsync } = useUpdateProject();
    const { t } = useTranslation();
    const user = useAuthStore((state) => state.user)
    const queryClient = useQueryClient()

    const [form] = Form.useForm();

    const handleSubmit = async () => {
        const values = await form.validateFields();

        await asyncHandler(mutateAsync.bind(null, { ...values, project_id }), {
            successMessage: t('messages.success.edit.projects', { name }),
            errorMessage: t('messages.error.edit.projects', { name }),
            onSuccess: () => {
                queryClient.invalidateQueries({
                    queryKey: [streamQueryKeys.statList]
                })
            },
        })
    };

    const showParallels = user?.role === EUserRole.ADMIN

    const { data, isLoading } = useQuery(projectQueries.freeStreams(project_id, {
        enabled: showParallels && open
    }))

    return (
        <ModalButton
            buttonProps={ {
                type: 'text',
                variant: 'filled',
            } }
            icon={ <EditOutlined/> }
            modalProps={ {

                title: t('project.buttons.edit_project'),
                centered: true,
                okText: t('project.buttons.save'),
                cancelText: t('project.buttons.cancel'),
                onOk: handleSubmit,
                destroyOnClose: true,
                onClose: () => {
                    form.resetFields()
                    setOpen(false)
                }
            } }
            onOpenModal={ setOpen.bind(null, true) }
            closeAfterOk
        >
            <ProjectForm
                extraItems={
                    showParallels ?
                        <MaxParallelsInput
                            freeCount={ Number(data) }
                            initialCountValue={ initialValues?.parallel_exec }
                            isLoading={ isLoading }
                            label={ t('project.inputs.max_parallels.label') }
                            name={ 'parallel_exec' }
                        />
                        : undefined
                }
                form={ form }
                initialValues={ initialValues }
            />
        </ModalButton>
    );
};

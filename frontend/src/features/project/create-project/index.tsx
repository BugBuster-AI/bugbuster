import { asyncHandler } from '@Common/utils';
import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { MaxParallelsInput } from '@Components/MaxParallelsInput';
import { ModalButton } from '@Components/ModalButton';
import { useAuthStore } from '@Entities/auth/store/auth.store';
import { ProjectForm } from '@Entities/project/components/ProjectForm';
import { projectQueries } from '@Entities/project/queries';
import { useCreateProject } from '@Entities/project/queries/mutations';
import { streamQueryKeys } from '@Entities/stream/queries/query-keys.ts';
import { EUserRole } from '@Entities/users/models';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Form, Skeleton, Typography } from 'antd';
import includes from 'lodash/includes';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    disabled?: boolean
}

export const CreateProject = ({ disabled }: IProps): ReactElement => {
    const { mutateAsync } = useCreateProject();
    const { t } = useTranslation();
    const [form] = Form.useForm();
    const user = useAuthStore((state) => state.user)
    const queryClient = useQueryClient()
    const workspace = useWorkspaceStore((state) => state.workspace)

    const handleSubmit = async () => {
        const values = await form.validateFields();

        await asyncHandler(mutateAsync.bind(null, values), {
            successMessage: t('project.messages.created'),
            onSuccess: () => {
                form.resetFields()
                queryClient.invalidateQueries({
                    queryKey: [streamQueryKeys.statList]
                })
            }
        })
    };

    const showParallels = user?.role === EUserRole.ADMIN

    const { data, isLoading, error } = useQuery(projectQueries.freeStreams(undefined, {
        enabled: showParallels
    }))

    const getParallelsInput = () => {
        if (isLoading) {
            return <Skeleton.Input/>
        }

        if (!!error) {
            const errorMessage = getErrorMessage({ error, needConvertResponse: true })

            return <Typography.Text type={ 'danger' }>{errorMessage}</Typography.Text>
        }

        return (
            <MaxParallelsInput
                freeCount={ Number(data) }
                label={ t('project.inputs.max_parallels.label') }
                name={ 'parallel_exec' }
            />
        )
    }

    const disabledRoles = [EUserRole.MEMBER, EUserRole.READ_ONLY]

    return (
        <ModalButton
            buttonProps={ {
                disabled: disabled || includes(disabledRoles, workspace?.role),
            } }
            buttonTitle={ t('project.buttons.new_project') }
            modalProps={ {
                title: 'Create project',
                centered: true,
                okButtonProps: {
                    disabled: !!error || isLoading
                },
                okText: t('project.buttons.create'),
                cancelText: t('project.buttons.cancel'),
                onOk: handleSubmit,
            } }
            closeAfterOk
        >
            <ProjectForm
                extraItems={
                    showParallels ?
                        getParallelsInput()
                        : undefined
                }
                form={ form }
            />
        </ModalButton>
    );
};

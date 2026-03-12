import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { EnvironmentForm, IEnvironmentFormValues } from '@Entities/environment/components';
import { ICreateEnvironmentPayload } from '@Entities/environment/models';
import { useCreateEnv } from '@Entities/environment/queries/mutations';
import { useProjectStore } from '@Entities/project/store';
import { Form } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

export const CreateEnvironment = (): ReactElement => {
    const { t } = useTranslation();
    const [form] = Form.useForm<IEnvironmentFormValues>();
    const navigate = useNavigate();
    const { mutateAsync } = useCreateEnv();
    const { id } = useParams();
    const projectId = useProjectStore((state) => state.currentProject)?.project_id;

    const onFinish = async (values: IEnvironmentFormValues) => {
        const { width, height, description, ...rest } = values;

        const resolution = {
            width: Number(width),
            height: Number(height)
        };

        const data: ICreateEnvironmentPayload = {
            ...rest,
            project_id: projectId!!,
            resolution,
            description: description || undefined
        };

        await asyncHandler(mutateAsync.bind(null, data), {
            successMessage: t('common.success_created'),
            errorMessage: null,
            onErrorValidate: ({ msg, field }) => {
                if (field) {
                    form.setFields([
                        {
                            name: field as keyof IEnvironmentFormValues,
                            errors: [msg],
                        },
                    ]);
                }
            },
            onSuccess: () => {
                if (id) {
                    navigate(PATHS.ENVIRONMENTS.ABSOLUTE(id));
                }
            }
        });
    };

    return (
        <EnvironmentForm
            form={ form }
            onFinish={ onFinish }
            showBrowserDefault
            showOsDefault
        />
    );
};

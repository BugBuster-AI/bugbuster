import { asyncHandler } from '@Common/utils';
import { EnvironmentForm, IEnvironmentFormValues } from '@Entities/environment/components';
import { IUpdateEnvironmentPayload } from '@Entities/environment/models';
import { envQueries } from '@Entities/environment/queries';
import { useUpdateEnv } from '@Entities/environment/queries/mutations';
import { useQuery } from '@tanstack/react-query';
import { Form } from 'antd';
import get from 'lodash/get';
import { ReactElement, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

export const EditEnvironment = (): ReactElement => {
    const { t } = useTranslation();
    const [form] = Form.useForm<IEnvironmentFormValues>();
    const { environmentId } = useParams();
    const { mutateAsync, isPending } = useUpdateEnv(environmentId!);
    const { data: initialData, isLoading } = useQuery(
        envQueries.envById(environmentId!!, !!environmentId)
    );

    const onFinish = async (values: IEnvironmentFormValues) => {
        const { width, height, description, ...rest } = values;

        const resolution = {
            width: Number(width),
            height: Number(height)
        };

        const data: IUpdateEnvironmentPayload = {
            ...rest,
            resolution,
            description: description || undefined
        };

        if (!environmentId) return;

        await asyncHandler(mutateAsync.bind(null, { id: environmentId!!, data }), {
            successMessage: t('common.success_updated'),
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
        });
    };

    const initialValues = useMemo(() => {
        if (!initialData) return undefined;

        const resolutionWidth = get(initialData, 'resolution.width', undefined);
        const resolutionHeight = get(initialData, 'resolution.height', undefined);

        return {
            title: initialData.title,
            description: initialData.description,
            browser: initialData.browser,
            operation_system: initialData.operation_system,
            width: resolutionWidth?.toString(),
            height: resolutionHeight?.toString(),
            retry_enabled: initialData.retry_enabled,
            retry_timeout: initialData.retry_timeout,
        } as IEnvironmentFormValues;
    }, [initialData]);

    return (
        <EnvironmentForm
            form={ form }
            initialValues={ initialValues }
            isLoading={ isLoading }
            isPending={ isPending }
            onFinish={ onFinish }
        />
    );
};

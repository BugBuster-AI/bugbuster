import { BaseLayout } from '@Common/components';
import { PATHS } from '@Common/consts';
import { IStep } from '@Common/types';
import { asyncHandler } from '@Common/utils';
import { formServerErrorHandler, httpStepToLocal, localStepToHttp } from '@Common/utils/test-case/steps.tsx';
import { LayoutTitle } from '@Components/LayoutTitle';
import { SharedStepForm } from '@Entities/shared-steps/components/Form';
import { IUpdateSharedStepPayload } from '@Entities/shared-steps/models';
import { sharedStepsQueries } from '@Entities/shared-steps/queries';
import { useUpdateSharedStep } from '@Entities/shared-steps/queries/mutations';
import { ITestCaseStep } from '@Entities/test-case/models';
import { useQuery } from '@tanstack/react-query';
import { Button, Flex, Form, Skeleton } from 'antd';
import isString from 'lodash/isString';
import map from 'lodash/map';
import { ReactElement, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

interface IUpdateSharedStepForm {
    name: string;
    description?: string;
    steps: IStep[]
}

export const EditSharedStep = (): ReactElement => {
    const { t } = useTranslation();
    const [form] = Form.useForm<IUpdateSharedStepForm>();
    const { id } = useParams()
    const { mutateAsync: updateSharedStep, isPending } = useUpdateSharedStep()
    const { sharedStepId } = useParams()
    const { data: initialData, isLoading } = useQuery(sharedStepsQueries.byId({ id: sharedStepId! }))
    const navigate = useNavigate()

    const handleBack = () => {
        if (id) {
            navigate(PATHS.SHARED_STEPS.ABSOLUTE(id))
        }
    }

    const initialPreparedValues = useMemo(() => {

        return {
            ...initialData,
            steps: map(initialData?.steps, (step, index) => httpStepToLocal(step, index))
        }
    }, [initialData])

    const onFinish = async (values: IUpdateSharedStepForm) => {
        const data: IUpdateSharedStepPayload = {
            ...values,
            steps: map(values?.steps, (el) => {
                if (isString(el) || !el) return el as unknown as ITestCaseStep

                return localStepToHttp(el)
            }),
        }

        if (!sharedStepId) return

        await asyncHandler(updateSharedStep.bind(null, { shared_steps_id: sharedStepId!!, ...data }), {
            successMessage: t('common.success_updated'),
            errorMessage: null,
            onErrorValidate: ({ msg, field }) => {
                if (field) {
                    form.setFields([
                        {
                            name: field as keyof IUpdateSharedStepForm,
                            errors: [msg],
                        },
                    ]);
                }
            },
            onSuccess: handleBack,
            onError: (error) => {

                formServerErrorHandler({
                    error,
                    form,
                    t
                })

                throw error
            }
        })
    };

    if (isLoading) {
        return <Skeleton/>
    }

    return (
        <SharedStepForm
            controlButtons={
                <Flex gap={ 8 } style={ { marginTop: 'auto' } }>
                    <Button htmlType={ 'submit' } loading={ isPending } type={ 'primary' }>{t('common.save')}</Button>
                    <Button htmlType={ 'button' } onClick={ handleBack }>{t('common.cancel')}</Button>
                </Flex>
            }
            form={ form }
            initialValues={ initialPreparedValues }
            onFinish={ onFinish }
        />
    )
};


export const SharedStepsEditPage = (): ReactElement => {
    const { id } = useParams()

    return <Flex style={ { height: '100%' } } vertical>
        <LayoutTitle
            backPath={ id ? PATHS.SHARED_STEPS.ABSOLUTE(id) : undefined }
            title={ `Edit shared step` }
            withBack
        />

        <BaseLayout style={ { flex: 1, width: 720 } }>
            <EditSharedStep/>
        </BaseLayout>
    </Flex>
}


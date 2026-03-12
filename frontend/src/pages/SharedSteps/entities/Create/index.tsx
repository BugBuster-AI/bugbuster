import { BaseLayout } from '@Common/components';
import { PATHS } from '@Common/consts';
import { IStep } from '@Common/types';
import { asyncHandler } from '@Common/utils';
import { formServerErrorHandler, localStepToHttp } from '@Common/utils/test-case/steps.tsx';
import { LayoutTitle } from '@Components/LayoutTitle';
import { useProjectStore } from '@Entities/project/store';
import { SharedStepForm } from '@Entities/shared-steps/components/Form';
import { ICreateSharedStepPayload } from '@Entities/shared-steps/models';
import { useCreateSharedStep } from '@Entities/shared-steps/queries/mutations';
import { Button, Flex, Form } from 'antd';
import isString from 'lodash/isString';
import map from 'lodash/map';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';


interface ICreateSharedStepForm {
    name: string;
    description?: string;
    steps: IStep[]
}

export const CreateSharedStep = (): ReactElement => {
    const { t } = useTranslation();
    const [form] = Form.useForm<ICreateSharedStepForm>();
    const navigate = useNavigate()
    const { mutateAsync, isPending } = useCreateSharedStep()
    const { id } = useParams()
    const projectId = useProjectStore((state) => state.currentProject)?.project_id

    const handleBack = () => {
        if (id) {
            navigate(PATHS.SHARED_STEPS.ABSOLUTE(id))
        }
    }

    const onFinish = async (values: ICreateSharedStepForm) => {

        const data = {
            ...values,
            steps: map(values?.steps, (el) => {
                if (isString(el) || !el) return el

                return localStepToHttp(el)
            }),
            project_id: projectId!!,
        } as ICreateSharedStepPayload

        await asyncHandler(mutateAsync.bind(null, data), {
            successMessage: t('common.success_created'),
            errorMessage: null,
            onErrorValidate: ({ msg, field }) => {
                if (field) {
                    form.setFields([
                        {
                            name: field as keyof ICreateSharedStepForm,
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

    return (
        <SharedStepForm
            controlButtons={
                <Flex gap={ 8 } style={ { marginTop: 'auto' } }>
                    <Button htmlType={ 'submit' } loading={ isPending } type={ 'primary' }>{t('common.save')}</Button>
                    <Button htmlType={ 'button' } onClick={ handleBack }>{t('common.cancel')}</Button>
                </Flex>
            }
            form={ form }
            onFinish={ onFinish }
        />
    )
};


export const SharedStepsCreatePage = (): ReactElement => {
    const { id } = useParams()

    return <Flex style={ { height: '100%' } } vertical>
        <LayoutTitle
            backPath={ id ? PATHS.SHARED_STEPS.ABSOLUTE(id) : undefined }
            title={ 'Create shared step' }
            withBack
        />

        <BaseLayout style={ { flex: 1, width: 720 } }>
            <CreateSharedStep/>
        </BaseLayout>
    </Flex>
}


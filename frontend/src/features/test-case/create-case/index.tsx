import { PATHS } from '@Common/consts';
import { IApiErrorDetail, IError } from '@Common/types';
import { asyncHandler } from '@Common/utils';
import { useProjectStore } from '@Entities/project/store';
import { recordQueries } from '@Entities/records/queries';
import { EStepGroup } from '@Entities/runs/models';
import { useSuiteStore } from '@Entities/suite/store';
import { TestCaseForm } from '@Entities/test-case/components/Form';
import {
    formServerErrorHandler,
    reverseTransformCaseData,
    transformUpdatedCaseData
} from '@Entities/test-case/components/Form/helper.tsx';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ITestCase, ITestCaseCreateFromRecordPayload, ITestCaseCreatePayload } from '@Entities/test-case/models';
import { useCreateTestCase } from '@Entities/test-case/queries';
import { createAndRun } from '@Features/test-case/create-case/create-and-run';
import { useQuery } from '@tanstack/react-query';
import { Button, Flex, Form, message } from 'antd';
import { AxiosError } from 'axios';
import get from 'lodash/get';
import head from 'lodash/head';
import isEmpty from 'lodash/isEmpty';
import { FC, ReactElement, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

interface IStep {
    step: string;
    type?: EStepType; // Только для testCasesSteps
}

export interface ICreateFormValues {
    name: string;
    suite_id: string;
    type: string;
    status: string;
    priority: string;
    url: string;
    before_steps: IStep[];
    steps: IStep[];
    after_steps: IStep[];
}

export const CreateForm: FC = (): ReactElement => {
    const { t } = useTranslation();
    const [searchParams] = useSearchParams()
    const selectedSuite = useSuiteStore((state) => state.selectedSuite);
    const suiteId = searchParams.get('suiteId') || selectedSuite?.suite_id;
    const project = useProjectStore((state) => state.currentProject)
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false)
    const { mutateAsync: createCaseAsync } = useCreateTestCase()
    const navigate = useNavigate()

    /* ********************************** */
    /* ******* Create by record id ***** */
    /********************************* */

    const recordId = searchParams.get('recordId')

    const {
        data: recordData,
        isLoading: recordIsLoading,
    } = useQuery(recordQueries.showFull({
        happy_pass_id: recordId!,
        project_id: project?.project_id!
    }, !!recordId && !!project?.project_id))

    const recordItem = head(recordData?.items || [])
    /* TODO: Нужен рефакторинг позже */
    const recordInitialValues = useMemo(
        () => reverseTransformCaseData(recordItem as unknown as ITestCase),
        [recordData]
    )

    const handleSubmitFromRecord = async (): Promise<ITestCase | null> => {
        const formData = form.getFieldsValue()
        let response: ITestCase | null = null

        setLoading(true)

        const updatedData = transformUpdatedCaseData(formData)
        const formattedData = {
            ...updatedData,
            happy_pass_id: recordItem?.happy_pass_id,
        } as unknown as ITestCaseCreateFromRecordPayload

        await asyncHandler(createCaseAsync.bind(null, formattedData), {
            successMessage: null,
            errorMessage: null,
            onFinally: () => {
                setLoading(false)
            },
            onSuccess: (data) => {
                const suiteId = data.suite_id

                if (!isEmpty(data.validation_reason)) {
                    message.warning(t('messages.warning.create.test_case'))
                    navigate(PATHS.REPOSITORY.EDIT_CASE.ABSOLUTE(data.project_id!, data.case_id))

                    return
                }

                navigate(PATHS.REPOSITORY.ABSOLUTE(data.project_id!))

                response = data
                message.success(t('messages.success.create.test_case'))
                form.resetFields()

                if (project) {
                    navigate(`${PATHS.REPOSITORY.ABSOLUTE(data.project_id!)}?suiteId=${suiteId}`)
                }
            },
            onError: async (e) => {
                formServerErrorHandler({
                    error: e,
                    form,
                    t
                })
            }
        })
        setLoading(false)

        return response
    }

    // Создание кейса
    const handleCreateCase = async () => {
        const formData = form.getFieldsValue()

        const formattedData = transformUpdatedCaseData(formData)

        await form.validateFields()

        try {
            const response = await createCaseAsync(formattedData as unknown as ITestCaseCreatePayload)

            if (!isEmpty(response.validation_reason)) {
                message.warning(t('messages.warning.create.test_case'))
                navigate(PATHS.REPOSITORY.EDIT_CASE.ABSOLUTE(response.project_id!, response.case_id))

                return response
            }

            message.success(t('messages.success.create.test_case'))

            return response
        } catch (e) {
            const errorResponse = e as AxiosError;
            const error = errorResponse.response?.data as IError | IApiErrorDetail;

            formServerErrorHandler({
                error,
                form,
                t
            })

            throw e
        }
    }

    // Создание тест кейса (сабмит функция)
    const handleSubmit = async () => {
        setLoading(true)

        if (recordId) {
            return await handleSubmitFromRecord()
        }

        try {
            const response = await handleCreateCase()

            form.resetFields()
            const currentSuite = response?.suite_id

            navigate(`${PATHS.REPOSITORY.ABSOLUTE(response?.project_id!)}?suiteId=${currentSuite}`)

        } catch (e) {
            console.error(e)
        } finally {
            setLoading(false)
        }

    }

    // Создание кейса и запуск
    const handleCreateAndRun = async () => {
        setLoading(true)
        try {
            await form.validateFields()
            const response = await handleCreateCase()

            if (!response) {
                throw new Error('Create case error')
            }

            await createAndRun({
                t,
                navigate,
                caseId: response.case_id
            })
        } catch (error) {
            console.error('save error:', error)
            const errorField = get(error, 'errorFields', undefined)?.[0]

            if (!errorField) {
                message.error('Error')

                return
            }
            if (errorField) {
                //@ts-ignore
                form.scrollToField(errorField?.name?.[0], {
                    behavior: 'smooth',
                    block: 'center',
                })
            }
        } finally {

            setLoading(false)
        }

    };

    const initialValues = useMemo(() => {
        return {
            suite_id: suiteId || null,
            steps: [
                { step: '', type: EStepType.STEP, stepGroup: EStepGroup.STEPS },
                { step: '', type: EStepType.RESULT, stepGroup: EStepGroup.STEPS },
            ],

            ...recordInitialValues,
        }
    }, [recordInitialValues])

    /*
     * if (recordId && !recordInitialValues) {
     *     return <Spin/>
     * }
     */

    return (
        <TestCaseForm
            buttonsToolbar={ (
                <Form.Item style={ { margin: 0, paddingBottom: '24px' } }>
                    <Flex align={ 'center' } gap={ 8 }>

                        <Button htmlType="submit" type="primary">
                            {t('create_test_case.save')}
                        </Button>

                        <Button htmlType="button" onClick={ handleCreateAndRun }>
                            {t('create_test_case.save_run')}
                        </Button>

                        <Button htmlType="button" onClick={ () => navigate(-1) }>
                            {t('create_test_case.cancel')}
                        </Button>
                    </Flex>
                </Form.Item>
            ) }
            form={ form }
            formProps={ {
                layout: 'vertical',
                onFinish: handleSubmit
            } }
            initialValues={ initialValues }
            isLoading={ recordIsLoading }
            isPending={ loading }
            needForceUpdateAfterChangeInitial
        />
    )
};

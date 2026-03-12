import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { useProjectStore } from '@Entities/project/store';
import { TestCaseForm } from '@Entities/test-case/components/Form';
import {
    formServerErrorHandler,
    reverseTransformCaseData,
    transformUpdatedCaseData
} from '@Entities/test-case/components/Form/helper.tsx';
import { ITestCase, ITestCaseUpdatePayload } from '@Entities/test-case/models';
import { caseQueries, useUpdateTestCase } from '@Entities/test-case/queries';
import { createAndRun } from '@Features/test-case/create-case/create-and-run';
import { useQuery } from '@tanstack/react-query';
import { Button, Flex, Form, Input, message, Result, Spin } from 'antd';
import isEmpty from 'lodash/isEmpty';
import { FC, ReactElement, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

interface IProps {
    onDataReady?: (data: ITestCase) => void
}

export const EditForm: FC<IProps> = ({ onDataReady }): ReactElement => {
    const { t } = useTranslation();
    const [form] = Form.useForm();
    const { caseId } = useParams()
    const { mutateAsync } = useUpdateTestCase()
    const { data, isLoading: caseDataLoading, isError, isFetching } = useQuery(caseQueries.byId(caseId!!,
        { refetchOnWindowFocus: false }
    ))
    const [isLoading, setIsLoading] = useState(false)
    const project = useProjectStore((state) => state.currentProject)
    const navigate = useNavigate()
    const { id } = useParams()

    const initialValues = useMemo(() => reverseTransformCaseData(data), [data])

    useEffect(() => {
        if (onDataReady && data) {
            onDataReady(data)
        }
    }, [data]);

    const onSubmit = async (needRedirect = true) => {
        setIsLoading(true)
        try {
            await form.validateFields()
            const formData = form.getFieldsValue()

            /*
             * HINT: логика удаления скринов, пока пусть будет
             * const pathsToDelete = map(STEP_GROUPS_TO_MAP, (stepKey) => {
             *     const items = get(formData, stepKey, [])
             */

            /*
             *     return compact(map(items, (item: IStep) => {
             *         if (item.tempFormData?.isDeleteContextScreenshot) {
             *             return item.extraData?.context_screenshot_path
             *         }
             */
            
            /*
             *         return null
             *     })
             *     )}
             * )?.flat()
             */
            
            const formattedData = transformUpdatedCaseData(formData)

            await asyncHandler(mutateAsync.bind(null, formattedData as unknown as ITestCaseUpdatePayload), {
                errorMessage: null,
                successMessage: null,
                onSuccess: async (data) => {
                    if (!isEmpty(data.validation_reason)) {
                        message.warning(t('messages.warning.update.test_case'))
                    } else {
                        /*
                         * try {
                         *     await Promise.all(
                         *         pathsToDelete.map((path) => deleteScreenshot({ minio_path: path }))
                         *     )
                         * } catch (e) {
                         *     console.error(e, 'Error deleting context screenshots')
                         * }
                         */
                        message.success(t('messages.success.update.test_case'))
                        if (needRedirect) {

                            const suiteId = data.suite_id

                            if (project) {
                                navigate(`${PATHS.REPOSITORY.ABSOLUTE(data.project_id!)}?suiteId=${suiteId}`)
                            }
                        }
                    }
                },
                onError: (e) => {
                    formServerErrorHandler({
                        error: e,
                        form,
                        t
                    })

                }
            })
        } catch (e) {
            throw e
        } finally {
            if (needRedirect) {
                setIsLoading(false)
            }
        }
    };

    const saveAndRun = async () => {
        setIsLoading(true)
        try {
            await onSubmit(false)

            if (data?.case_id) {
                await createAndRun({
                    t,
                    navigate,
                    caseId: data?.case_id
                })
            }

        } catch (e) {
            // form.submit()
            await form.validateFields()
            throw e
        } finally {
            setIsLoading(false)
        }

    }

    if (isFetching || caseDataLoading) return <Spin/>

    if (isError) {
        return (
            <Result
                extra={
                    <Button onClick={ () => navigate('/') }>
                        {t('common.api_error')}
                    </Button>
                }
                status="warning"
                title={ t('common.api_error') }
            />
        )
    }

    return (
        <TestCaseForm
            buttonsToolbar={ (
                <Form.Item style={ { margin: 0, paddingBottom: '24px' } }>
                    <Flex align={ 'center' } gap={ 8 }>

                        <Button htmlType="submit" type="primary">
                            {t('create_test_case.save')}
                        </Button>

                        <Button htmlType="button" onClick={ saveAndRun }>
                            {t('create_test_case.save_run')}
                        </Button>

                        <Button
                            htmlType="button"
                            onClick={ () => {
                                form.resetFields()
                                navigate(PATHS.REPOSITORY.ABSOLUTE(id!))
                            } }>
                            {t('create_test_case.cancel')}
                        </Button>
                    </Flex>
                </Form.Item>
            ) }
            form={ form }
            formProps={ {
                layout: 'vertical',
                onFinish: onSubmit,
            } }
            hiddenFields={
                <Form.Item name={ 'case_id' } hidden>
                    <Input/>
                </Form.Item>
            }
            initialValues={ {
                ...initialValues
            } }
            isInitError={ isError }
            isLoading={ isFetching || caseDataLoading }
            isPending={ isLoading }
        />
    );
};

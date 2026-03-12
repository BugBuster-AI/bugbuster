import { AsyncSelect } from '@Common/components';
import { AppearanceAnimation } from '@Common/components/Animations/Appearance';
import { asyncHandler } from '@Common/utils';
import { IEnvironmentListItem } from '@Entities/environment';
import { envQueries } from '@Entities/environment/queries';
import { useProjectStore } from '@Entities/project/store';
import { ICreateGroupedRunPayload } from '@Entities/runs/models';
import { EExecutionMode } from '@Entities/runs/models/enum';
import { runsQueries } from '@Entities/runs/queries';
import { useCreateGroupRun, useEditGroupRun } from '@Entities/runs/queries/mutations';
import { streamQueries } from '@Entities/stream/queries';
import { ParallelCasesForm } from '@Features/runs/create-run-from-cases/components/ParallelCasesForm';
import { SequentialCasesForm } from '@Features/runs/create-run-from-cases/components/SequentialCasesForm';
import { ICaseWithExecution, useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { VariableKitSelect } from '@Features/variable/kit-select';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { DatePicker, Flex, Form, Input, message, Typography } from 'antd';
import dayjs from 'dayjs';
import flatMap from 'lodash/flatMap';
import map from 'lodash/map';
import values from 'lodash/values';
import { forwardRef, useEffect, useImperativeHandle } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

interface IRunForm {
    name: string;
    description: string;
    environment_id: string;
    host: string;
    variables: string
    deadline: Date;
}

export interface IFormRef {
    submit: () => Promise<void>
}

interface IProps {
    afterSubmit?: () => void
}

export const CreateRunForm = forwardRef<IFormRef, IProps>(({ afterSubmit }, ref) => {
    const { id } = useParams()
    const selectedCases = useCreateRunStore((state) => state.selectedCaseId)
    const project = useProjectStore((state) => state.currentProject)
    const initialData = useCreateRunStore((state) => state.initialData)
    const isEdit = useCreateRunStore((state) => state.isEdit)
    const setMaxParallelThreads = useCreateRunStore((state) => state.setMaxParallelThreads)
    const selectedParallelThreads = useCreateRunStore((state) => state.selectedParallelThreads)
    const { mutateAsync } = useCreateGroupRun()
    const { mutateAsync: editMutate } = useEditGroupRun()
    const { t } = useTranslation()
    const queryClient = useQueryClient()
    const [form] = Form.useForm<IRunForm>()
    const sizeCases = flatMap(values(selectedCases), (cases) => map(cases, 'id')).length

    const allCasesFlat = flatMap(values(selectedCases), (cases) => cases as ICaseWithExecution[])

    const allCases = [
        ...allCasesFlat
            .filter((c) => c.executionMode === EExecutionMode.SEQUENTIAL)
            .sort((a, b) => (a.executionOrder ?? 0) - (b.executionOrder ?? 0))
            .map((c, index) => ({
                case_id: c.id,
                execution_mode: 'sequential' as const,
                execution_order: index + 1
            })),
        ...allCasesFlat
            .filter((c) => c.executionMode === EExecutionMode.PARALLEL)
            .map((c) => ({
                case_id: c.id,
                execution_mode: 'parallel' as const,
                execution_order: null
            }))
    ]

    // Get max threads for the project
    const { data: freeStreams, isLoading: isStreamsLoading } = useQuery(runsQueries.freeStreams(id!, {
        enabled: !!id
    }))

    useEffect(() => {
        if (freeStreams) {
            setMaxParallelThreads(Number(freeStreams))
        }
    }, [freeStreams, setMaxParallelThreads])

    const onFinish = async () => {
        const formData = form.getFieldsValue()
        const deadline = formData?.deadline
            ? dayjs(new Date(formData.deadline)).add(3, 'hours').toISOString()
            : undefined

        const hasCases = allCases.length > 0

        const data = {
            environment_id: formData.environment_id,
            name: formData.name,
            cases: allCases,
            host: formData.host,
            description: formData.description,
            project_id: project?.project_id!,
            deadline,
            variables: formData.variables,
            parallel_exec: hasCases ? selectedParallelThreads : undefined
        } as ICreateGroupedRunPayload

        if (isEdit && initialData) {
            await asyncHandler(editMutate.bind(null, { id: initialData.id, data }), {
                onSuccess: () => {
                    afterSubmit && afterSubmit()
                    queryClient.invalidateQueries(streamQueries.statList())
                },
                onErrorValidate: ({ msg, field }) => {
                    if (field && form) {
                        form.setFields([{
                            //@ts-ignore
                            name: String(field),
                            errors: [msg]
                        }])
                    }
                }
            })

            return
        }

        await asyncHandler(mutateAsync.bind(null, data), {
            errorMessage: null,
            onError: (e) => {
                if (typeof (e.detail) !== 'string') {
                    message.error('Validate error')

                    return
                }
                message.error(e.detail)
            },
            onSuccess: () => {
                afterSubmit && afterSubmit()
            },
            onErrorValidate: ({ msg, field }) => {
                if (field && form) {
                    form.setFields([{
                        //@ts-ignore
                        name: String(field),
                        errors: [msg]
                    }])
                }
            }
        })
    };

    useImperativeHandle(ref, () => ({
        submit: async () => await onFinish()
    }));

    return (
        <Form<IRunForm>
            className="middle-form-margin"
            form={ form }
            id="runForm"
            initialValues={ {
                name: initialData?.name,
                description: initialData?.data?.description,
                environment_id: initialData?.data?.environment,
                host: initialData?.data?.host,
                deadline: initialData?.data?.deadline ? dayjs(initialData?.data?.deadline) : undefined,
                parallel_exec: initialData,
                variables: initialData?.data?.variables
            } }
            layout="vertical"
            onFinish={ onFinish }
        >
            <Form.Item
                label={ t('create_group.name') }
                name="name"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <Input/>
            </Form.Item>
            <Form.Item
                label={ t('create_group.description') }
                name="description"
            >
                <Input.TextArea/>
            </Form.Item>
            <Form.Item
                label={ t('create_group.environment') }
                name="environment_id"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <AsyncSelect<IEnvironmentListItem>
                    defaultValue={ null }
                    keyIndex={ 'environment_id' }
                    labelIndex={ 'title' }
                    queryOptions={ envQueries.envList(id!) }
                />

            </Form.Item>

            <Form.Item
                label={ t('variables.select.label') }
                name={ 'variables' }
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                {project && <VariableKitSelect projectId={ project.project_id }/>}
            </Form.Item>

            <Form.Item
                label={ t('create_group.host') }
                name="host"
                rules={ [
                    {
                        type: 'url',
                        message: t('errors.input.url')
                    },
                ] }
            >
                <Input/>
            </Form.Item>
            <Form.Item
                label={ t('create_group.deadline') }
                name="deadline"
            >
                <DatePicker style={ { width: 320 } }/>
            </Form.Item>

            {/* <Divider orientation="left" orientationMargin={ 0 } plain>
                <Typography.Title level={ 5 }>{t('create_run.execution_modes')}</Typography.Title>
            </Divider> */}

            <AppearanceAnimation visible={ !isStreamsLoading }>
                <Flex gap={ 24 } vertical>
                    <ParallelCasesForm />
                    <SequentialCasesForm />
                </Flex>
            </AppearanceAnimation>

            <Flex
                align="center"
                gap={ 8 }
                style={ { padding: '8px 0 4px' } }
            >
                <Typography.Text type="secondary">
                    {t('create_run.selected_cases')}:
                </Typography.Text>
                <Typography.Text strong>
                    {sizeCases}
                </Typography.Text>
            </Flex>

            {/* <Form.Item
                name="cases"
                rules={ [{
                    required: true,
                    message: t('create_group.case_error'),
                    validator: () =>
                        (sizeCases ? Promise.resolve() : Promise.reject(t('create_group.case_error')))
                }] }
            >
                <Flex align={ 'flex-start' } gap={ 16 } vertical>
                    <Typography.Text>
                        {t('create_run.size_testcase', { count: sizeCases })}
                        <Button
                            disabled={ !sizeCases }
                            icon={ <DeleteOutlined/> }
                            onClick={ setCases.bind(null, {}) }
                            size={ 'small' }
                            style={ { marginLeft: 8 } }
                        />
                    </Typography.Text>

                    <Button onClick={ setStep.bind(null, 2) } variant={ 'text' }>{t('create_run.select_cases')}</Button>
                </Flex>
            </Form.Item> */}

        </Form>
    )
})


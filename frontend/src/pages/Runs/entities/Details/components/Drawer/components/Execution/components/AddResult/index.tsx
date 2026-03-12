import { InboxOutlined } from '@ant-design/icons';
import { ToolsApi } from '@Common/api';
import { useThemeToken } from '@Common/hooks';
import { asyncHandler } from '@Common/utils';
import { Uploader } from '@Components/Uploader';
import { ERunStatus, IMedia } from '@Entities/runs/models';
import { useCompleteFailRunQuery } from '@Entities/runs/queries/mutations';
import { useTestCaseStore } from '@Entities/test-case';
import { SetFinalTestStatus } from '@Features/test-case/set-final-statuses';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Flex, Form, Input, Modal, ModalProps, Typography } from 'antd';
import isNil from 'lodash/isNil';
import size from 'lodash/size';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    open?: boolean,
    onClose?: () => void
    stepIndex?: number
    defaultStatus?: ERunStatus
    runIds?: string[]
    isStatusChangeable?: boolean
    defaultValues?: IForm
    reflectionIndex?: number
    onSuccess?: (status: ERunStatus) => void
}

interface IForm {
    status: ERunStatus,
    comment?: string
    attachments?: File[]
}

const toolsApi = ToolsApi.getInstance()

export const AddRunResult =
    ({
        open,
        onClose,
        stepIndex,
        defaultStatus,
        runIds,
        defaultValues,
        onSuccess,
        isStatusChangeable = true,
        reflectionIndex
    }: IProps) => {
        const { t } = useTranslation()
        const token = useThemeToken()
        const [openModal, setOpenModal] = useState(open)
        const currentCase = useTestCaseStore((state) => state.currentCase)
        const runItem = useGroupedRunStore((state) => state.runItem)
        const [form] = Form.useForm<IForm>()
        const { mutateAsync, isPending } = useCompleteFailRunQuery(runItem?.group_run_id!)

        const handleClose = () => {
            setOpenModal(false)
        }

        const handleSubmit = async () => {
            await form.validateFields()
            const data = form.getFieldsValue()
            const attachments = data.attachments

            let error = undefined
            let medias: IMedia[] | undefined | null = undefined

            if (size(attachments)) {
                const formData = new FormData();

                attachments?.forEach((file) => {
                    formData.append('files', file);
                });

                medias = await asyncHandler(toolsApi.uploadFiles.bind(null, formData), {
                    successMessage: null,
                    onSuccess: (data) => medias = data,
                    // @ts-ignore
                    onError: () => error = true
                })

                if (!!error) {
                    return
                }
            }

            if (!!error) return

            if (!currentCase && runIds) {
                await asyncHandler(mutateAsync.bind(null, {
                    run_ids: runIds,
                    failed_step_index: !isNil(stepIndex) ? Number(stepIndex) : undefined,
                    status: data.status,
                    comment: data.comment,
                    reflection_step_index: !isNil(reflectionIndex) ? Number(reflectionIndex) : undefined,
                    attachments: medias || undefined
                }), {
                    onSuccess: handleClose
                })
            }
            if (currentCase?.actual_run_id) {
                const data = form.getFieldsValue()

                await asyncHandler(mutateAsync.bind(null, {
                    run_ids: runIds || [currentCase.actual_run_id],
                    failed_step_index: !isNil(stepIndex) ? Number(stepIndex) : undefined,
                    status: data.status,
                    comment: data.comment,
                    reflection_step_index: !isNil(reflectionIndex) ? Number(reflectionIndex) : undefined,
                    //@ts-ignore
                    attachments: medias || undefined
                }), {
                    onSuccess: handleClose
                })
            }
        }

        const handleFinish = async () => {
            try {
                const data = form.getFieldsValue()

                await handleSubmit()
                onSuccess?.(data.status)
            } catch (e) {
                throw e
            }
        }

        const props: ModalProps = {
            width: 720,
            open: openModal,
            onOk: handleFinish,
            afterClose: onClose,
            onCancel: handleClose,
            okText: t('group_run.add_result.ok'),
            cancelText: t('group_run.add_result.cancel'),
            centered: true,
            title: (
                <Flex gap={ 4 } vertical>
                    <Typography.Title level={ 5 }>
                        {t('group_run.add_result.title')}
                    </Typography.Title>
                    <Typography.Text style={ { color: token.colorTextDescription } }>
                        {t('group_run.add_result.subtitle')}
                    </Typography.Text>
                </Flex>
            )
        }

        useEffect(() => {
            if (defaultStatus) {
                form.setFields([{
                    name: 'status',
                    value: defaultStatus,
                }])
            }
        }, [form, defaultStatus]);

        return (
            <Modal
                { ...props }
                destroyOnClose={ true }
                okButtonProps={ {
                    loading: isPending
                } }
                closable
            >
                {open && <Form<IForm>
                    form={ form }
                    initialValues={ {
                        status: defaultStatus,
                        comment: defaultValues?.comment,
                        attachments: defaultValues?.attachments
                    } }
                    layout={ 'vertical' }
                >
                    <Flex gap={ 16 } vertical>
                        <Form.Item
                            name={ 'status' }
                            noStyle={ !isStatusChangeable }
                            rules={ [{
                                validator: (_, value) => {
                                    if (isNil(value)) {
                                        return Promise.reject('Статус не должен быть undefined');
                                    }

                                    return Promise.resolve();
                                },
                                message: t('group_run.errors.select_status')
                            }] }
                            style={ { marginBottom: 4 } }
                        >
                            {isStatusChangeable && <SetFinalTestStatus selectable/>}
                        </Form.Item>
                        <Form.Item
                            label={ t('group_run.add_result.comment') }
                            name={ 'comment' }
                            style={ { marginBottom: 0 } }
                        >
                            <Input.TextArea
                                placeholder={ t('group_run.add_result.placeholder') }
                                title={ t('group_run.add_result.comment') }
                            />
                        </Form.Item>
                        <Form.Item name={ 'attachments' }>
                            <Uploader
                                defaultFileList={ defaultValues?.attachments }
                                disabled={ isPending }
                                onDropFile={ (files) => {
                                    form.setFieldValue('attachments', files)
                                } }
                                type={ 'dragger' }>
                                <p className="ant-upload-drag-icon">
                                    <InboxOutlined style={ { color: token.colorTextQuaternary } }/>
                                </p>
                                <Typography.Text className={ 'ant-upload-hint' }>
                                    {t('group_run.add_result.drop')}
                                </Typography.Text>
                            </Uploader>
                        </Form.Item>
                    </Flex>
                </Form>}
            </Modal>
        )
    }

import { asyncHandler } from '@Common/utils';
import { ModalButton } from '@Components/ModalButton';
import { useProjectStore } from '@Entities/project/store';
import { IUpdateSuite } from '@Entities/suite/models';
import {  useUpdateSuite } from '@Entities/suite/queries/mutations.ts';
import { useSuiteStore } from '@Entities/suite/store';
import { SuiteSelect } from '@Features/suite/suite-selects';
import { Form, Input } from 'antd';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    initialValue?: Partial<IUpdateSuite>
    renderButton?: ({ onClick }: {onClick: () => void}) => ReactNode
}

export const EditSuite = ({ renderButton, initialValue }: IProps): ReactElement => {
    const { t } = useTranslation()
    const projectId = useProjectStore((state) => state.currentProject)?.project_id
    const addButton = `${t('repository_page.toolbar.addSuite')}`
    const selectedSuite = useSuiteStore((state) => state.selectedSuite)
    const { mutateAsync, isPending } = useUpdateSuite()

    const [form] = Form.useForm<IUpdateSuite>()

    const onSubmit = async () => {
        const data = form.getFieldsValue()
        const filteredData = { ...data }

        await asyncHandler(mutateAsync.bind(null, filteredData as IUpdateSuite), {
            errorMessage: t('messages.success.error.suite'),
            successMessage: t('messages.success.create.suite'),
        })
    }

    return (
        <ModalButton
            buttonProps={ {
                loading: isPending
            } }
            buttonTitle={ addButton }
            modalProps={ {
                onOk: onSubmit,
                title: t('suite.create.title'),
                okText: t('suite.create.submit'),
                cancelText: t('suite.create.cancel'),
                centered: true,
                destroyOnClose: true
            } }
            renderButton={ renderButton }
            closeAfterOk
            needFixKeyDown
        >
            <Form<IUpdateSuite>
                className="middle-form-margin"
                form={ form }
                initialValues={ initialValue }
                layout={ 'vertical' }
                preserve={ false }
                style={ { marginBottom: '32px' } }
            >
                <Form.Item
                    label={ t('suite.inputs.name.label') }
                    name="name"
                    rules={ [{
                        required: true,
                        message: t('errors.input.required')
                    }] }>
                    <Input placeholder={ t('suite.inputs.name.placeholder') } />
                </Form.Item>

                <Form.Item initialValue={ projectId } name="suite_id" hidden>
                    <Input />
                </Form.Item>

                <Form.Item
                    initialValue={ selectedSuite?.suite_id || null }
                    label={ t('suite.inputs.parent_suite.label') }
                    name="parent_id"
                >
                    <SuiteSelect />
                </Form.Item>

                <Form.Item
                    label={ t('suite.inputs.description.label') }
                    name="description"
                >
                    <Input.TextArea
                        maxLength={ 400 }
                        placeholder={ t('suite.inputs.description.placeholder') }
                        style={ { height: '120px', resize: 'none' } }
                        showCount
                    />
                </Form.Item>
            </Form>
        </ModalButton>
    )
}

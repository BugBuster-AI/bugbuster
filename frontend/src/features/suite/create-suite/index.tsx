import { asyncHandler } from '@Common/utils';
import { ModalButton } from '@Components/ModalButton';
import { ICreateSuitePayload } from '@Entities/suite/models';
import { useCreateSuite } from '@Entities/suite/queries/mutations.ts';
import { useSuiteStore } from '@Entities/suite/store';
import { SuiteSelect } from '@Features/suite/suite-selects';
import { Form, Input } from 'antd';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

interface IProps {
    initialValue?: Partial<ICreateSuitePayload>
    renderButton?: ({ onClick }: { onClick: () => void }) => ReactNode
}

export const CreateSuite = ({ renderButton, initialValue }: IProps): ReactElement => {
    const { t } = useTranslation()
    const { id } = useParams()
    const addButton = `${t('repository_page.toolbar.addSuite')}`
    const selectedSuite = useSuiteStore((state) => state.selectedSuite)

    const { mutateAsync, isPending } = useCreateSuite()

    const [form] = Form.useForm<ICreateSuitePayload>()

    const onSubmit = async () => {
        const data = form.getFieldsValue()
        const filteredData = { ...data }

        await asyncHandler(mutateAsync.bind(null, filteredData as ICreateSuitePayload), {
            errorMessage: t('messages.success.error.suite'),
            successMessage: t('messages.success.create.suite')
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
                destroyOnClose: true,
            } }
            renderButton={ renderButton }
            closeAfterOk
            needFixKeyDown
        >
            <Form
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
                    <Input placeholder={ t('suite.inputs.name.placeholder') }/>
                </Form.Item>

                <Form.Item initialValue={ id } name="project_id" hidden>
                    <Input/>
                </Form.Item>

                <Form.Item
                    initialValue={ selectedSuite?.suite_id || null }
                    label={ t('suite.inputs.parent_suite.label') }
                    name="parent_id"
                >
                    {/*<Input*/}
                    {/*    placeholder={ t('suite.inputs.parent_suite.placeholder') }*/}
                    {/*    disabled*/}
                    {/*/>*/}
                    <SuiteSelect/>
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

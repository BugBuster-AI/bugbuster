import { asyncHandler } from '@Common/utils';
import { IContactUsPayload } from '@Entities/billing/models';
import { useContactUs } from '@Entities/billing/queries/mutations.ts';
import { Button, Flex, Form, Input } from 'antd';
import FormItem from 'antd/es/form/FormItem';
import { useTranslation } from 'react-i18next';

type TForm = IContactUsPayload

interface IProps {
    onClose?: () => void
    onFinish?: () => void
}

export const ContactUs = ({ onClose, onFinish }: IProps) => {
    const [form] = Form.useForm<TForm>()

    const { t } = useTranslation()

    const { mutateAsync } = useContactUs()

    const onSubmit = async () => {
        const data = form.getFieldsValue()

        await asyncHandler(mutateAsync.bind(null, data), {
            onSuccess: () => {
                form.resetFields()
                onFinish?.()
            }
        })
    }

    return (
        <Form<TForm>
            form={ form }
            layout={ 'vertical' }
            onFinish={ onSubmit }
            style={ { marginTop: 16 } }
            clearOnDestroy
        >
            <FormItem
                label={ t('contactUs.username') }
                name={ 'username' }
                rules={ [{ required: true, message: t('errors.input.required') }] }
                style={ { marginBottom: '12px' } }>
                <Input placeholder={ t('contactUs.usernamePlaceholder') }/>
            </FormItem>
            <FormItem
                label={ t('contactUs.email') }
                name={ 'email' }
                rules={ [{ required: true, message: t('errors.input.required') }] }
                style={ { marginBottom: '12px' } }>
                <Input placeholder={ t('contactUs.emailPlaceholder') }/>
            </FormItem>
            <FormItem
                label={ t('contactUs.message') }
                name={ 'question' }
                rules={ [{ required: true, message: t('errors.input.required') }] }>
                <Input.TextArea placeholder={ t('contactUs.messagePlaceholder') }/>
            </FormItem>
            <Flex gap={ 8 } justify={ 'flex-end' }>
                {onClose && <Button htmlType={ 'button' } onClick={ onClose }>{t('contactUs.cancel')}</Button>}
                <Button htmlType={ 'submit' } type={ 'primary' }>{t('contactUs.submit')}</Button>
            </Flex>
        </Form>
    )
}

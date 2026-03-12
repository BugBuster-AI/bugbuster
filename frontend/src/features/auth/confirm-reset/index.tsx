import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { IPasswordResetConfirm } from '@Entities/auth';
import { AuthApi } from '@Entities/auth/api';
import { FormWrapper } from '@Entities/auth/components/FormWrapper';
import { ValidItem } from '@Features/auth/signup/components/ValidItem.tsx';
import { Button, Flex, Form, Input, message } from 'antd';
import includes from 'lodash/includes';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';

type TForm = Omit<IPasswordResetConfirm, 'token'>

const authUrl = AuthApi.getInstance()

export const ConfirmResetForm = () => {
    const { t } = useTranslation()
    const [loading, setLoading] = useState(false)
    const [form] = Form.useForm<TForm>()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const onSubmit = async () => {
        const data = form.getFieldsValue()
        const token = searchParams.get('token')

        if (token) {
            setLoading(true)
            await asyncHandler(authUrl.resetPasswordConfirm.bind(null, {
                new_password: data.new_password,
                token
            }), {
                successMessage: t('auth.confirm_reset.success'),
                onSuccess: () => navigate(PATHS.AUTH.LOGIN.ABSOLUTE)
            })
            setLoading(false)
        } else {
            message.error(t('auth.confirm_reset.no_token'))
        }
    }

    return <FormWrapper label={ t('auth.confirm_reset.submit') }>
        <Form<TForm>
            form={ form }
            layout="vertical"
            onFinish={ onSubmit }
            style={ { display: 'flex', gap: '40px', flexDirection: 'column' } }
        >
            <Flex gap={ 24 } vertical>
                <Form.Item
                    className={ 'no-error' }
                    help={ null }
                    label={ t('auth.confirm_reset.new_password') }
                    name="new_password"
                    rules={ [
                        { min: 8, message: '1' },
                        { pattern: /^(?=.*[a-z])(?=.*[A-Z]).+$/, message: '2' },
                        { pattern: /^(?=.*\d).+$/, message: '3' },
                        { pattern: /^(?=.*[.,:?!*+%@#]).+$/, message: '4' },
                        { required: true, message: '5' },
                    ] }
                    style={ { marginBottom: 0 } }
                >
                    <Input.Password placeholder={ t('auth.confirm_reset.placeholder') } size="large"/>
                </Form.Item>
                <Form.Item
                    noStyle
                    shouldUpdate
                >
                    {() => {
                        const value = form.getFieldValue('new_password')
                        const errors = form.getFieldError('new_password')

                        return <Flex gap={ 4 } style={ { marginBlock: '8px 24px' } } vertical>
                            <ValidItem
                                isValid={ !includes(errors, '1') && value }
                                label={ t('auth.signup.condition_1') }/>
                            <ValidItem
                                isValid={ !includes(errors, '2') && value }
                                label={ t('auth.signup.condition_2') }/>
                            <ValidItem
                                isValid={ !includes(errors, '3') && value }
                                label={ t('auth.signup.condition_3') }/>
                            <ValidItem
                                isValid={ !includes(errors, '4') && value }
                                label={ t('auth.signup.condition_4') }/>
                        </Flex>
                    }}
                </Form.Item>
            </Flex>

            <Button
                htmlType={ 'submit' }
                loading={ loading }
                size="large"
                style={ { width: '100%' } }
                type={ 'primary' }
                variant={ 'filled' }
            >
                {t('auth.confirm_reset.submit')}
            </Button>
        </Form>
    </FormWrapper>
}

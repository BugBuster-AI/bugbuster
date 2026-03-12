import { EStatus } from '@Common/types';
import { asyncHandler } from '@Common/utils';
import { ISignupPayload } from '@Entities/auth';
import { AuthApi } from '@Entities/auth/api';
import { FormWrapper } from '@Entities/auth/components/FormWrapper';
import { ValidItem } from '@Features/auth/signup/components/ValidItem.tsx';
import { Button, Flex, Form, Input, Typography } from 'antd';
import includes from 'lodash/includes';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';

type TSignupForm = Omit<ISignupPayload, 'username'> & {
    confirmPassword: string
}

const authApi = AuthApi.getInstance()

export const Signup = (): ReactElement => {
    const { t } = useTranslation()
    const [form] = Form.useForm<TSignupForm>()
    const navigate = useNavigate()
    const onSubmit = async () => {
        const data = form.getFieldsValue()
        const apiData = {
            password: data.password,
            username: data.email,
            email: data.email
        } as ISignupPayload

        await asyncHandler(authApi.singup.bind(null, apiData), {
            onSuccess: () => navigate('/auth/login')
        })
    }

    return (
        <FormWrapper
            label={ 'Get started' }
            subtitle={
                <Typography.Text>
                    Do you already have an account? <Link to={ '/auth/login' }>Sign In</Link>
                </Typography.Text>
            }
        >
            <Form<TSignupForm>
                form={ form }
                layout="vertical"
                onFinish={ onSubmit }
                style={ { display: 'flex', gap: '40px', flexDirection: 'column' } }
            >
                <Flex vertical>
                    <Form.Item
                        label={ t('auth.email.label') }
                        name="email"
                        rules={ [
                            { required: true, message: t('errors.input.required') }
                        ] }>
                        <Input placeholder={ t('auth.email.placeholder') } size="large"/>
                    </Form.Item>


                    <Form.Item
                        className={ 'no-error' }
                        help={ null }
                        label={ t('auth.password.label') }
                        name="password"
                        rules={ [
                            { min: 8, message: '1' },
                            { pattern: /^(?=.*[a-z])(?=.*[A-Z]).+$/, message: '2' },
                            { pattern: /^(?=.*\d).+$/, message: '3' },
                            { pattern: /^(?=.*[.,:?!*+%@#]).+$/, message: '4' },
                            { required: true, message: '5' },
                        ] }
                        style={ { marginBottom: 0 } }
                    >
                        <Input.Password size="large"/>
                    </Form.Item>
                    <Form.Item
                        noStyle
                        shouldUpdate
                    >
                        {() => {
                            const value = form.getFieldValue('password')
                            const errors = form.getFieldError('password')

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

                    <Form.Item
                        dependencies={ ['password'] }
                        label={ t('auth.confirm_password.label') }
                        name="confirmPassword"
                        rules={ [
                            { required: true, message: t('errors.input.required') },
                            ({ getFieldValue }) => ({
                                validator (_, value) {
                                    if (!value || getFieldValue('password') === value) {
                                        return Promise.resolve();
                                    }

                                    return Promise.reject(new Error('The new password that you entered do not match!'));
                                },
                            }),
                        ] }
                        style={ { marginBottom: 0 } }
                    >
                        <Input.Password size="large"/>

                    </Form.Item>

                </Flex>
                <Form.Item
                    // extra={ <Typography.Text type="danger">{error}</Typography.Text> }
                    label={ null }
                    style={ { margin: 0 } }
                >
                    <Button
                        htmlType="submit"
                        loading={ status === EStatus.LOADING }
                        size="large"
                        style={ { width: '100%' } }
                        type={ 'primary' }
                        variant={ 'filled' }
                    >
                        {t('auth.login.title')}
                    </Button>
                </Form.Item>
            </Form>
        </FormWrapper>
    )
}

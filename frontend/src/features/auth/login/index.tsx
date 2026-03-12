import { GoogleOutlined } from '@ant-design/icons';
import { BACKEND_URL } from '@Common/api';
import { PATHS } from '@Common/consts';
import { EStatus } from '@Common/types';
import { ILoginPayload } from '@Entities/auth';
import { FormWrapper } from '@Entities/auth/components/FormWrapper';
import { useAuthStore } from '@Entities/auth/store/auth.store';
import { Button, Divider, Flex, Form, Input, message, Tooltip, Typography } from 'antd';
import axios from 'axios';
import { ReactElement, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';


export const Login = (): ReactElement => {
    const [googleLoading, setGoogleLoading] = useState<boolean>(false)
    const { t } = useTranslation()
    const { login, error, status } = useAuthStore()

    const onSubmit = async (data: ILoginPayload): Promise<void> => {
        await login(data)
    }

    const handleGoogleLogin = async () => {
        setGoogleLoading(true);

        const url = `${BACKEND_URL}auth/google-login`

        try {
            const response = await axios.get(
                url
            );

            const { authorization_url } = response.data;

            window.location.href = authorization_url;
        } catch {
            message.error('Failed to initiate Google login. Please try again.');
        } finally {
            setGoogleLoading(false);
        }
    };

    return (
        <FormWrapper
            label={ t('auth.login.title') }
            subtitle={
                <Typography.Text>
                    {t('auth.dont_have_account')} <Link to={ '/auth/signup' }>{t('auth.signup_button')}</Link>
                </Typography.Text>
            }
        >
            <Form<ILoginPayload>
                layout="vertical"
                onFinish={ onSubmit }
            >
                <Flex style={ { marginBottom: '40px' } } vertical>
                    <Form.Item
                        label={ t('auth.email.label') }
                        name="username"
                        rules={ [
                            { required: true, message: t('errors.input.required') }
                        ] }>
                        <Input placeholder={ t('auth.email.placeholder') } size="large"/>
                    </Form.Item>

                    <Form.Item
                        label={ t('auth.password.label') }
                        name="password"
                        rules={ [
                            { required: true, message: t('errors.input.required') }
                        ] }
                        style={ { marginBottom: 0 } }
                    >
                        <Input.Password size="large"/>

                    </Form.Item>

                    <Tooltip title={ t('auth.login.forgot_pass') }>
                        <Link
                            style={ { display: 'block', marginTop: '4px', width: 'fit-content', marginLeft: 'auto' } }
                            to={ PATHS.AUTH.RESET_PASS.ABSOLUTE }
                        >
                            {t('auth.login.forgot_pass')}
                        </Link>
                    </Tooltip>
                </Flex>

                {error && <Typography.Text style={ { display: 'block', marginBlock: '8px' } } type={ 'danger' }>
                    {error}
                </Typography.Text>}

                <Form.Item
                    label={ null }
                    style={ { margin: 0 } }
                    noStyle
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

            <Divider>Or</Divider>

            <Button
                icon={ <GoogleOutlined/> }
                loading={ googleLoading }
                onClick={ handleGoogleLogin }
                size={ 'large' }
                style={ { marginBottom: 16 } }
                block
            >
                Continue with Google
            </Button>

        </FormWrapper>
    )
}

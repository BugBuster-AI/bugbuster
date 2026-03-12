import { LANGUAGE } from '@Common/consts/env';
import { asyncHandler } from '@Common/utils';
import { IResetPasswordPayload } from '@Entities/auth';
import { AuthApi } from '@Entities/auth/api';
import { FormWrapper } from '@Entities/auth/components/FormWrapper';
import { Button, Flex, Form, Input, Typography } from 'antd';
import { ReactElement, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

const authApi = AuthApi.getInstance()


function formatTimer (seconds: number): string {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    const formattedSeconds = remainingSeconds < 10 ? `0${remainingSeconds}` : remainingSeconds;

    return `${minutes}:${formattedSeconds}`;
}

export const ResetPassword = (): ReactElement => {
    const { t } = useTranslation()
    const language = LANGUAGE
    const [loading, setLoading] = useState(false)
    const [success, setSuccess] = useState(false)
    const [timer, setTimer] = useState(0)
    const emailRef = useRef<string | null>(null)
    const timerRef = useRef<NodeJS.Timeout | null>(null)
    const [form] = Form.useForm<Omit<IResetPasswordPayload, 'language'>>()

    const onSubmit = async () => {
        const data = form.getFieldsValue()

        const email = emailRef?.current || data.email

        setLoading(true)
        await asyncHandler(authApi.requestResetPassword.bind(null, {
            language,
            email
        }), {
            onSuccess: () => {
                emailRef.current = email
                setSuccess(true)
                setTimer(60)
                const countdown = setInterval(() => {
                    setTimer((prev) => {
                        if (prev <= 1) {
                            clearInterval(countdown)

                            return 0
                        }

                        return prev - 1
                    })
                }, 1000)

                timerRef.current = countdown
            }
        })
        setLoading(false)
    }

    useEffect(() => {
        return () => {
            if (timerRef.current) {
                clearInterval(timerRef.current)
            }
        }
    }, [])

    const buttonTitle = success
        ? timer > 0
            ? `${t('auth.reset.resend')} ${formatTimer(timer)}`
            : t('auth.reset.resend')
        : t('auth.reset.title')

    return <FormWrapper label={ t('auth.reset.title') }>

        <Form<Omit<IResetPasswordPayload, 'language'>>
            form={ form }
            layout="vertical"
            onFinish={ onSubmit }
            style={ { display: 'flex', gap: '40px', flexDirection: 'column' } }
        >
            <Flex gap={ 24 } vertical>
                <Typography.Text>
                    {success
                        ? t('auth.reset.resend_text', { email: emailRef.current })
                        : t('auth.reset.step_1')}
                </Typography.Text>

                {!success && <Form.Item
                    label={ t('auth.email.label') }
                    name={ 'email' }
                    rules={ [
                        { required: true, message: t('errors.input.required') }
                    ] }
                    style={ { marginBottom: 0 } }
                >
                    <Input placeholder={ t('auth.email.placeholder') } size="large"/>
                </Form.Item>}

            </Flex>

            <Button
                disabled={ timer > 0 }
                htmlType={ 'submit' }
                loading={ loading }
                size="large"
                style={ { width: '100%' } }
                type={ 'primary' }
                variant={ 'filled' }
            >
                {buttonTitle}
            </Button>
        </Form>
    </FormWrapper>
}

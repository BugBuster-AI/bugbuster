import { AppearanceAnimation } from '@Common/components/Animations/Appearance';
import { Checkbox, Divider, Flex, Form, FormInstance, InputNumber, Typography } from 'antd';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { RETRY_CONFIG, retryValidator } from './helper';
import styles from './RetryTimeoutInput.module.scss'

interface IProps {
    form: FormInstance
}

export const RetryTimeoutInput = ({ form }: IProps) => {
    const wrapperRef = useRef<HTMLDivElement | null>(null)
    const { t } = useTranslation()
    const retryTimeout = Form.useWatch('retry_timeout', form);

    const isRetryEnabled = Form.useWatch('retry_enabled', form);

    const getRetryTimeoutStatus = () => {
        if (!retryTimeout || retryTimeout <= RETRY_CONFIG.WARNING_TIMEOUT) {
            return null;
        }
        if (retryTimeout > RETRY_CONFIG.MAX_TIMEOUT) {
            return 'error';
        }

        return 'warning';
    };

    const getRetryTimeoutMessage = () => {
        const status = getRetryTimeoutStatus();

        if (status === 'error') {
            return t('environment.retry.error.maxTimeout', { max: RETRY_CONFIG.MAX_TIMEOUT });
        }

        if (status === 'warning') {
            return t('environment.retry.error.slowTestCase');
        }

        return undefined;
    };

    const handleBlur = () => {
        if (retryTimeout && retryTimeout > RETRY_CONFIG.MAX_TIMEOUT) {
            form.setFieldValue('retry_timeout', RETRY_CONFIG.MAX_TIMEOUT);
        }
    };

    return <Flex ref={ wrapperRef } className={ styles.retryWrapper } gap={ 4 } vertical>
        <AppearanceAnimation
            trigger={
                <Flex gap={ 16 } vertical>
                    <Typography.Title level={ 5 } style={ { margin: 0 } }>
                        {t('environment.retry.title')}
                    </Typography.Title>
                    <Form.Item
                        name="retry_enabled"
                        style={ { marginBottom: 0 } }
                        valuePropName="checked"
                    >
                        <Checkbox
                            className={ styles.retryCheckbox }
                            onChange={ (e) => {
                                form.setFieldValue('retry_enabled', e.target.checked);
                                setTimeout(() => {
                                    if (!e.target.checked) return
                                    wrapperRef?.current?.scrollIntoView({ behavior: 'smooth' })
                                }, 250)
                                if (!e.target.checked) {
                                    form.setFieldValue('retry_timeout', null);
                                }
                            } }
                        >
                            <Flex align={ 'flex-start' } vertical>
                                <Typography.Text>
                                    {t('environment.retry.enable.label')}
                                </Typography.Text>
                                <Typography.Text style={ { fontSize: 12 } } type="secondary">
                                    {t('environment.retry.enable.description')}
                                </Typography.Text>
                            </Flex>
                        </Checkbox>
                    </Form.Item>
                </Flex>
            }
            visible={ isRetryEnabled }>
       
            <Flex className={ styles.retrySettings } gap={ 8 } vertical>
                <Form.Item
                    help={ getRetryTimeoutMessage() }
                    label={ t('environment.retry.timeout.label') }
                    name="retry_timeout"
                    rules={ [
                        { required: isRetryEnabled, message: t('errors.input.required') },
                        {
                            validator: (_, value) => retryValidator(t, value)
                        },
                    ] }
                    style={ { marginBottom: 0 } }
                    validateStatus={ getRetryTimeoutStatus() || undefined }
                >
                    <InputNumber
                        addonAfter="sec"
                        min={ 1 }
                        onBlur={ handleBlur }
                        placeholder={ t('environment.retry.timeout.placeholder') }
                        style={ { width: '100%' } }
                    />
                </Form.Item>
                <Typography.Text style={ { fontSize: 12 } } type="secondary">
                    {t('environment.retry.timeout.description')}
                </Typography.Text>
            </Flex>
     
        </AppearanceAnimation>
        <Divider style={ { marginBlock: `24px 0` } }/>
    </Flex>
}

import { AsyncSelect } from '@Common/components/AsyncSelect';
import { RetryTimeoutInput } from '@Entities/environment/components/Form/components/RetryTimeoutInput';
import { envQueries } from '@Entities/environment/queries';
import {
    Button,
    Divider,
    Form,
    FormInstance,
    FormProps,
    Input,
    Skeleton,
} from 'antd';
import upperFirst from 'lodash/upperFirst';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';


export interface IEnvironmentFormValues {
    title: string;
    description?: string | null;
    browser: string;
    operation_system: string;
    width: string;
    height: string;
    retry_enabled?: boolean;
    retry_timeout?: number;
}

interface IProps {
    form: FormInstance<IEnvironmentFormValues>;
    onFinish: (values: IEnvironmentFormValues) => void;
    initialValues?: IEnvironmentFormValues;
    isLoading?: boolean;
    isPending?: boolean;
    formProps?: FormProps;
    buttonsToolbar?: ReactNode;
    showBrowserDefault?: boolean;
    showOsDefault?: boolean;
}

export const EnvironmentForm = ({
    form,
    onFinish,
    initialValues,
    isLoading = false,
    isPending = false,
    formProps,
    buttonsToolbar,
    showBrowserDefault = false,
    showOsDefault = false,
}: IProps): ReactElement => {
    const { t } = useTranslation();

    if (isLoading) {
        return <Skeleton/>;
    }


    return (
        <Form<IEnvironmentFormValues>
            form={ form }
            initialValues={ initialValues }
            layout="vertical"
            onFinish={ onFinish }
            style={ { display: 'flex', flexDirection: 'column', flex: 1 } }
            { ...formProps }
        >
            <Form.Item
                label={ t('environment.name.label') }
                name="title"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <Input placeholder={ t('environment.name.placeholder') }/>
            </Form.Item>

            <Form.Item
                label={ t('environment.description.label') }
                name="description"
            >
                <Input.TextArea placeholder={ t('environment.description.placeholder') }/>
            </Form.Item>

            <Form.Item
                label={ t('environment.browser.label') }
                name="browser"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <AsyncSelect
                    defaultValue={ showBrowserDefault ? null : undefined }
                    labelTransform={ (label) => upperFirst(label) }
                    onLoadData={
                        showBrowserDefault
                            ? (data) => form.setFieldValue('browser', data?.[1])
                            : undefined
                    }
                    placeholder={ t('environment.browser.placeholder') }
                    queryOptions={ envQueries.browserList() }
                />
            </Form.Item>

            <Form.Item
                label={ t('environment.operationSystem.label') }
                name="operation_system"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <AsyncSelect
                    defaultValue={ showOsDefault ? null : undefined }
                    labelTransform={ (label) => upperFirst(label) }
                    onLoadData={
                        showOsDefault
                            ? (data) => form.setFieldValue('operation_system', data?.[2])
                            : undefined
                    }
                    placeholder={ t('environment.operationSystem.placeholder') }
                    queryOptions={ envQueries.osList() }
                    disabled
                />
            </Form.Item>

            <Form.Item
                label={ t('environment.width.label') }
                name="width"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <Input placeholder={ t('environment.width.placeholder') }/>
            </Form.Item>

            <Form.Item
                label={ t('environment.height.label') }
                name="height"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <Input placeholder={ t('environment.height.placeholder') }/>
            </Form.Item>

            <Divider style={ { marginBlock: `0px 24px` } }/>

            <RetryTimeoutInput form={ form }/>

            {buttonsToolbar || (
                <Form.Item style={ { marginBlock: 'auto 12px' } }>
                    <Button htmlType="submit" loading={ isPending } type="primary">
                        {t('environment.submit')}
                    </Button>
                </Form.Item>
            )}
        </Form>
    );
};


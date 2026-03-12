import { Form, FormProps, Input } from 'antd';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export interface IVariableKitForm {
    name: string;
    description?: string
}

interface IProps extends FormProps<IVariableKitForm> {
}

export const VariableKitForm = ({ form, initialValues, ...props }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage' })

    useEffect(() => {

        if (initialValues && form) {
            form.setFieldsValue(initialValues)
        }
    }, [initialValues, form]);

    
    return (
        <Form<IVariableKitForm>
            form={ form }
            layout={ 'vertical' }
            style={ { marginTop: 16 } }
            clearOnDestroy
            { ...props }
        >
            <Form.Item
                label={ t('create.inputs.name.title') }
                name={ 'name' }
                rules={ [{ required: true, message: t('validation.required') }] }
            >
                <Input placeholder={ t('create.inputs.name.placeholder') }/>
            </Form.Item>
            <Form.Item label={ t('create.inputs.description.title') } name={ 'description' }>
                <Input.TextArea
                    maxLength={ 100 }
                    placeholder={ t('create.inputs.description.placeholder') }
                    showCount
                />
            </Form.Item>
        </Form>
    )
}

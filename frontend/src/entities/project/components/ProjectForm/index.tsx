import { Form, FormInstance, FormProps, Input } from 'antd';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps<T> extends Omit<FormProps<T>, 'form'> {
    form: FormInstance<T>
    extraItems?: ReactNode
}

export interface IBaseProjectForm {
    name: string
    description: string
}

export const ProjectForm = <T extends IBaseProjectForm, >({ form, extraItems, ...props }: IProps<T>) => {
    const { t } = useTranslation()

    return <Form form={ form } layout="vertical" clearOnDestroy { ...props }>
        <Form.Item
            label={ t('project.inputs.name.label') }
            name="name"
            rules={ [{ required: true, message: t('errors.input.required') }] }
        >
            <Input placeholder={ t('project.inputs.name.placeholder') }/>
        </Form.Item>
        <Form.Item
            label={ t('project.inputs.description.label') }
            name="description"
        >
            <Input.TextArea placeholder={ t('project.inputs.description.placeholder') }/>
        </Form.Item>
        {extraItems}
    </Form>
}

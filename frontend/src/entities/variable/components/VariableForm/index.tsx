import { VariableType } from '@Entities/variable/models/types';
import {  Form, FormProps, Input, Radio } from 'antd';
import isEmpty from 'lodash/isEmpty';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { VariableTypes } from './consts';
import { TimeVariableSettings } from './TimeVariableSettings';

export interface IVariableForm {
    isLoading?: boolean
    variable_name: string;
    variable_description?: string | null;
    variable_config: {
        type: 'simple' | 'time';
        value?: string;
        base?: string;
        utc_offset?: string;
        shifts?: Array<{
            value: number | string;
            type: string;
        }>;
        format?: string;
        'is-const'?: boolean;
    };
    customFormat?: string;
    variable_details_id?: string;
    variables_kit_id?: string;
}

interface IProps extends FormProps<IVariableForm> {
    isLoading?: boolean
}



export const VariableForm = ({ form, initialValues, isLoading, ...props }: IProps) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage.details' })
    const variableType = Form.useWatch(['variable_config', 'type'], form)
    const initialValuesAlreadySet = useRef(false);

    useEffect(() => {
        if (initialValues && form && !initialValuesAlreadySet.current && !isEmpty(initialValues)) {
            form.setFieldsValue(initialValues)
            initialValuesAlreadySet.current = true;
        }
    }, [initialValues, form]);
    
    return (
        <Form<IVariableForm>
            form={ form }
            layout={ 'vertical' }
            style={ { marginTop: 16 } }
            clearOnDestroy
            { ...props }
        >
            <Form.Item
                label={ t('create.inputs.name.title') }
                name="variable_name"
                rules={
                    [
                        { required: true, message: t('validation.required') },
                        { max: 255, message: t('validation.maxLength', { max: 255 }) },
                        {
                            pattern: /^[A-Za-z0-9_]+$/,
                            message: t('validation.latinNoSpaces')
                        }
                    ]
                }
            >
                <Input placeholder={ t('create.inputs.name.placeholder') }/>
            </Form.Item>

            {/* === Новые поля === */}

            <Form.Item label={ t('create.inputs.description.title') } name="variable_description">
                <Input.TextArea placeholder={ t('create.inputs.description.placeholder') } />
            </Form.Item>
            <Form.Item
                label={ t('create.inputs.type.title') }
                name={ ['variable_config', 'type'] }
                style={ { marginBottom: 18 } }>
                <Radio.Group
                    defaultValue={ VariableType.simple }
                    options={ [
                        { value: VariableType.simple, label: t('create.inputs.type.simple') },
                        { value: VariableType.time, label: t('create.inputs.type.time') }
                    ] } />
            </Form.Item>

            {variableType === VariableTypes.TIME && (
                <TimeVariableSettings 
                    form={ form! }
                    kitId={ initialValues?.variables_kit_id } 
                />
            )}

            {variableType !== VariableTypes.TIME && (
                <Form.Item
                    label={ t('create.inputs.value.title') }
                    name={ ['variable_config', 'value'] }
                >
                    <Input
                        placeholder={ t('create.inputs.value.placeholder') }
                    />
                </Form.Item>
            )   
            }  

            {/* === === === */}

           
        </Form>
    )
}

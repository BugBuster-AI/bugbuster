import { HighlightTextarea } from '@Components/HighlightTextarea';
import { Form, FormInstance, Input, InputNumber, Select } from 'antd';
import map from 'lodash/map';
import { ComponentProps, createContext, FC, HTMLAttributes, PropsWithChildren, ReactNode } from 'react';

interface IEditableCellProps extends HTMLAttributes<HTMLElement> {
    editing: boolean;
    dataIndex: string;
    title: any;
    inputType: 'number' | 'text' | 'select';
    record: any
    index: number;
    selectOptions: ISelectOption[]
    form: FormInstance
    inputNode?: ReactNode
    highlightedTextareaProps?: {
        isHighlighted: boolean
    } & ComponentProps<typeof HighlightTextarea>
}

interface ISelectOption {
    label: string;
    value: string
}

export const EditableCell: FC<PropsWithChildren<IEditableCellProps>> = ({
    editing,
    dataIndex,
    title,
    style,
    inputType,
    record,
    index,
    children,
    inputNode: customInputNode,
    highlightedTextareaProps,
    selectOptions,
    form,
    ...restProps
}) => {


    const getInputNode = () => {
        const { isHighlighted, ...restHighlightedProps } = highlightedTextareaProps || {}

        if (isHighlighted) {
            return <HighlightTextarea { ...restHighlightedProps }/>
        }

        let inputNode: ReactNode = null

        switch (inputType) {
            case 'number':

                inputNode = <InputNumber/>
                break
            case 'select':
                inputNode = (
                    <Select defaultValue={ record?.[dataIndex] || '' }>
                        {map(selectOptions, (item) => {
                            return <Select.Option value={ item.value }>{item.label}</Select.Option>
                        })}
                    </Select>
                )
                break
            default:
                if (customInputNode) {
                    inputNode = customInputNode
                    break
                }
                inputNode = <Input/>
                break
        }

        return inputNode
    }

    const inputNode = getInputNode()

    const inputName = [record?.id, dataIndex]

    return (
        <td style={ style } { ...restProps }>
            {editing ? (
                <Form.Item
                    initialValue={ record?.[dataIndex] }
                    name={ inputName }
                    rules={ [
                        {
                            required: true,
                            message: `Please Input ${title}!`,
                        },
                    ] }
                    style={ { margin: 0 } }
                >
                    {inputNode}
                </Form.Item>
            ) : (
                children
            )}
        </td>
    );
};

interface IEditableRowProps {
    index: number;
}

const EditableContext = createContext<FormInstance | null>(null);

export const EditableRow: FC<IEditableRowProps> = ({ index, ...props }) => {
    const [form] = Form.useForm();

    return (
        <Form component={ false } form={ form }>
            <EditableContext.Provider value={ form }>
                <tr { ...props } />
            </EditableContext.Provider>
        </Form>
    );
};

export const arrayToOptions = (data: string[]) => {
    return map(data, (item) => {
        return {
            label: item,
            value: item
        }
    })
}

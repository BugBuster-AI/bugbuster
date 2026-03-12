import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { nanoid } from '@ant-design/pro-components';
import CheckIcon from '@Assets/icons/check-icon.svg?react';
import XMarkIcon from '@Assets/icons/xmark-icon.svg?react';
import { EditableCell } from '@Components/EditableCell';
import { Button, Flex, Form, FormInstance, FormProps, Table } from 'antd';
import { Popconfirm, TableProps } from 'antd/lib';
import assign from 'lodash/assign';
import every from 'lodash/every';
import filter from 'lodash/filter';
import includes from 'lodash/includes';
import map from 'lodash/map';
import { useEffect, useState } from 'react';

interface IProps {
    columns: any[]
    addText: string
    deleteText: string
    emptyObj: any
    form: FormInstance
    data: any,
    setData: (data: any) => void
    formProps?: FormProps
    onSaveRow?: (values: any[], id: string) => void
    onDeleteRow?: (values: any[], id: string) => void
}

export const EditableTable = ({
    form,
    emptyObj,
    data,
    setData,
    columns,
    addText,
    deleteText,
    formProps,
    onSaveRow,
    onDeleteRow,
}: IProps) => {
    const [editingKey, setEditingKey] = useState('')

    const isEditing = (record: any) => {
        return editingKey === record.id
    }

    const save = async (key: string) => {
        try {
            const row = (await form.validateFields())?.[key];

            const newData = [...data];
            const index = newData.findIndex((item) => key === item.id);

            if (index > -1) {
                const item = newData[index];

                newData.splice(index, 1, {
                    ...item,
                    ...row,
                });

                setData(newData);
                onSaveRow?.(newData, key)
                setEditingKey('');
            } else {
                newData.push(row);
                setData(newData);
                onSaveRow?.(newData, key)
                setEditingKey('')
            }
        } catch (errInfo) {
            console.error('Validate Failed:', errInfo);
        }
    };

    const handleAddKey = () => {
        const id = nanoid()
        const newData = {
            ...emptyObj,
            id
        };

        setEditingKey(id)
        setData((prev) => [...prev, newData]);
    }

    const handleDelete = (key: string) => {
        const newData = data.filter((item) => item.id !== key);

        onDeleteRow?.(newData, key)
        setData(newData);
    };

    const edit = (record) => {
        form.setFieldsValue({ ...record });
        setEditingKey(record.id);
    };

    const cancel = (record) => {
        const cloneData = assign({}, record)

        delete cloneData.id

        if (every(cloneData, (value) => !value)) {
            const newData = filter(data, (item) => item.id !== record.id);

            setData(newData);
        }
        setEditingKey('')
    };

    const commonColumns = [
        ...columns,
        {
            width: '100px',
            fixed: 'right',
            render: (_, record) => {
                const editable = isEditing(record);

                return <Flex gap={ 8 }>
                    {!editable ? (
                        <>
                            <Button icon={ <EditOutlined/> } onClick={ () => edit(record) } type={ 'text' }/>
                            <Popconfirm onConfirm={ () => handleDelete(record.id) } title={ deleteText }>
                                <Button icon={ <DeleteOutlined/> } type={ 'text' }/>
                            </Popconfirm>
                        </>
                    ) : <>
                        <Button
                            color={ 'green' }
                            icon={ <CheckIcon/> }
                            onClick={ () => save(record.id) }
                            size={ 'small' }
                            type="text"
                            variant={ 'solid' }
                        />
                        <Button
                            color={ 'danger' }
                            icon={ <XMarkIcon/> }
                            onClick={ () => cancel(record) }
                            size={ 'small' }
                            type="text"
                            variant={ 'solid' }
                        />
                    </>
                    }
                </Flex>
            }
        }
    ]
    const mergedColumns: TableProps['columns'] = commonColumns?.map((col) => {
        if (!col.editable) {
            return { ...col, style: { wordBreak: 'break-word', ...col.style, } }
        }

        return {
            ...col,
            onCell: (record) => ({
                record,
                dataIndex: col.dataIndex,
                inputType: col.inputType,
                selectOptions: col?.selectOptions,
                title: col.title,
                style: col?.editableStyles,
                editing: isEditing(record),
                form,
                highlightedTextareaProps: col?.highlightedTextareaProps as any,
            }),
        };

    });

    // очистка editingKey если удалили редактируемую строку
    useEffect(() => {
        if (includes(map(data, (item) => item.id), editingKey)) {
            return
        }
        setEditingKey('')
    }, [data]);

    return (
        <Form component={ false } form={ form } { ...formProps }>
            <Table
                key={ 'id' }
                columns={ mergedColumns }
                components={ {
                    body: { cell: EditableCell },
                } }
                dataSource={ data }
                locale={ { emptyText: null } }
                pagination={ false }
                rowClassName="editable-row"
                rowKey={ 'id' }
                size={ 'small' }
            />
            <Button
                disabled={ !!editingKey }
                icon={ <PlusOutlined/> }
                onClick={ handleAddKey }
                style={ { marginTop: 12 } }
                type={ 'text' }>
                {addText}
            </Button>
        </Form>
    )
}

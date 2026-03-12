import {
    EditableTable
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/EditableTable.tsx';
import {
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { addNanoid } from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import { IFormDataItem } from '@Entities/test-case/components/Form/components/CurlEditForm/models.ts';
import { Flex, Typography } from 'antd';
import { useForm } from 'antd/es/form/Form';
import map from 'lodash/map';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const FormData = () => {
    const [form] = useForm()
    const { t } = useTranslation('translation', { keyPrefix: 'apiForm.body.formData' })
    const { body, setBody } = useCurlEditFormDataSelector()
    const initialValue = body.formData || []
    const [data, setData] = useState(addNanoid(initialValue))

    const columns = [
        {
            key: 'id',
            title: t('key'),
            dataIndex: 'key',
            width: '50%',
            editable: true,
            render: (value, record) => {
                return <Flex gap={ 8 }>
                    <span
                        style={ {
                            fontWeight: 'bold',
                            wordBreak: 'break-word',
                            color: record.type === 'text' ? 'green' : 'orange'
                        } }>{record?.type?.toUpperCase()}</span>
                    {value}
                </Flex>
            }
        },
        {
            id: 'id',
            title: t('value'),
            dataIndex: 'value',
            width: '50%',
            editable: true,
            render: (value) => {
                return <Typography.Text style={ { wordBreak: 'break-word' } }>{value}</Typography.Text>
            }
        },
    ]

    const handleChange = (newData: IFormDataItem[]) => {
        setBody({
            formData: newData
        })
    }

    useEffect(() => {
        handleChange(map(data, (item) => ({
            key: item.key,
            value: item.value,
            type: item.type as 'text' | 'file'
        })))
    }, [data]);

    return (
        <EditableTable
            addText={ t('key') }
            columns={ columns }
            data={ data }
            deleteText={ t('delete') }

            emptyObj={ {
                key: '',
                value: '',
                type: 'text'
            } }
            form={ form }
            setData={ setData }
        />

    )
}

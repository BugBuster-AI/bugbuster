import {
    EditableTable
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/EditableTable.tsx';
import {
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { addNanoid } from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import { IDataObject } from '@Entities/test-case/components/Form/components/CurlEditForm/models.ts';
import { Typography } from 'antd';
import { useForm } from 'antd/es/form/Form';
import map from 'lodash/map';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const UrlEncoded = () => {
    const [form] = useForm()
    const { t } = useTranslation('translation', { keyPrefix: 'apiForm.body.urlEncoded' })
    const { body, setBody } = useCurlEditFormDataSelector()
    const initialValue = body.urlEncoded || []
    const [data, setData] = useState(addNanoid(initialValue))

    const columns = [
        {
            key: 'id',
            title: t('key'),
            dataIndex: 'key',
            width: '50%',
            editable: true,
            render: (value) => {
                return <Typography.Text style={ { wordBreak: 'break-word' } }>{value}</Typography.Text>
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

    const handleChange = (newData: IDataObject[]) => {
        setBody({
            urlEncoded: newData
        })
    }

    useEffect(() => {
        handleChange(map(data, (item) => ({
            key: item.key,
            value: item.value
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
                value: ''
            } }
            form={ form }
            setData={ setData }
        />

    )
}

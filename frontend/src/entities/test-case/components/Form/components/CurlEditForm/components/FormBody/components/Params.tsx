import {
    EditableTable
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/EditableTable.tsx';
import {
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { addNanoid, stringifyQueryArray } from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import { IParamEdit } from '@Entities/test-case/components/Form/components/CurlEditForm/models.ts';
import { Typography } from 'antd';
import { useForm } from 'antd/es/form/Form';
import qs from 'query-string';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const ParamsEdit = () => {
    const [form] = useForm()
    const { t } = useTranslation('translation', { keyPrefix: 'apiForm.params' })
    const { params, url, setUrl } = useCurlEditFormDataSelector()
    const [data, setData] = useState<IParamEdit[]>([])

    const columns = [
        {
            key: 'id',
            title: t('key'),
            dataIndex: 'key',
            width: '50%',
            editable: true,
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

    const generateUrl = (params: IParamEdit[]) => {

        const query = stringifyQueryArray(params)
        const { url: baseUrl } = qs.parseUrl(url || '')

        return `${baseUrl}?${query}`

    }

    const handleSaveRow = (data: IParamEdit[]) => {
        const fullUrl = generateUrl(data)

        if (fullUrl !== url) {
            setUrl(fullUrl)
        }
    }

    const handleDeleteRow = (data: IParamEdit[]) => {
        const fullUrl = generateUrl(data)

        if (fullUrl !== url) {
            setUrl(fullUrl)
        }
    }

    useEffect(() => {
        setData(addNanoid(params) as unknown as IParamEdit[])
    }, [params]);

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
            onDeleteRow={ handleDeleteRow }
            onSaveRow={ handleSaveRow }
            setData={ setData }
        />

    )
}

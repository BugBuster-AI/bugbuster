import { formatVariableToComponent, replaceWithReactNode } from '@Common/utils/formatVariable';
import {
    EditableTable
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/EditableTable.tsx';
import {
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { addNanoid } from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import { Form, Typography } from 'antd';
import map from 'lodash/map';
import { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

export const HeadersEdit = () => {
    const [form] = Form.useForm()
    const { t } = useTranslation('translation', { keyPrefix: 'apiForm.headers' })
    const { headers, setHeaders } = useCurlEditFormDataSelector()
    const [data, setData] = useState(addNanoid(headers))

    const columns = useMemo(() => [
        {
            title: t('key'),
            dataIndex: 'key',
            style:{
                maxWidth: '300px',
                width: '300px'
            },
            width: '50%',
            editable: true,
            render: (value) => {
                return <Typography.Text style={ { wordBreak: 'break-word' } }>{value}</Typography.Text>
            }
        },
        {
            title: t('value'),
            dataIndex: 'value',
            width: '50%',
            highlightedTextareaProps: {
                isHighlighted: true,
                initialVariables: [],
                renderInBody: true
            },
            render: (value) => {
                const formatted = replaceWithReactNode(value,
                    (variable) => formatVariableToComponent(variable, variable, true))
            
                return <Typography.Text style={ { wordBreak: 'break-word' } }>{formatted}</Typography.Text>
            },
            editable: true,
            editableStyles: {
                maxWidth: '300px',
                width: '300px'
            }
        },
    ], [t])

    useEffect(() => {
        setHeaders(map(data, (item) => ({
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

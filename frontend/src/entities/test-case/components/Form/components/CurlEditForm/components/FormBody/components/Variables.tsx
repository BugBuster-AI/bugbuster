import { formatVariableToComponent, replaceWithReactNode } from '@Common/utils/formatVariable.tsx';
import {
    EditableTable
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/EditableTable.tsx';
import {
    VARIABLES_AUTOCOMPLETE_LIST
} from '@Entities/test-case/components/Form/components/CurlEditForm/consts.ts';
import {
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { addNanoid } from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import { Form, Typography } from 'antd';
import map from 'lodash/map';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';


export const VariablesEdit = () => {
    const [form] = Form.useForm()
    const { t } = useTranslation('translation', { keyPrefix: 'apiForm.variables' })
    const { variables, setVariables } = useCurlEditFormDataSelector()
    const [data, setData] = useState(addNanoid(variables))

    const columns = [
        {
            title: t('variableName'),
            dataIndex: 'name',
            width: '50%',
            editable: true,
            style: {
                maxWidth: '300px',
                width: '300px'
            },
            render: (value) => {
                return <Typography.Text style={ { wordBreak: 'break-word' } }>{value}</Typography.Text>
            }
            
        },
        {
            title: t('responsePath'),
            dataIndex: 'path',
            width: '50%',
            highlightedTextareaProps: {
                isHighlighted: true,
                initialVariables: VARIABLES_AUTOCOMPLETE_LIST,
                renderInBody: true
            },
            render: (value) => {
                const formatted = replaceWithReactNode(value,
                    (variable) => formatVariableToComponent(variable, variable, true))

                return <Typography.Text style={ { wordBreak: 'break-word' } }>{formatted}</Typography.Text>
            },
            editableStyles: {
                maxWidth: '300px',
                width: '300px'
            },
            editable: true,
        },
    ]

    useEffect(() => {
        setVariables(map(data, (item) => ({
            name: item.name,
            path: item.path
        })))
    }, [data]);

    return (
        <EditableTable
            addText={ t('variable') }
            columns={ columns }
            data={ data }
            deleteText={ t('delete') }
            emptyObj={ {
                name: '',
                path: ''
            } }
            form={ form }
            setData={ setData }
        />
    )
}

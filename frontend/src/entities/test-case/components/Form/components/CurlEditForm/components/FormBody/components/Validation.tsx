import { VALIDATION_TYPES } from '@Common/consts/common.ts'
import { formatVariableToComponent, replaceWithReactNode } from '@Common/utils/formatVariable.tsx';
import { arrayToOptions } from '@Components/EditableCell';
import {
    EditableTable
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/EditableTable.tsx';
import { VALIDATION_AUTOCOMPLETE_LIST } from '@Entities/test-case/components/Form/components/CurlEditForm/consts.ts';
import {
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { addNanoid } from '@Entities/test-case/components/Form/components/CurlEditForm/helper.ts';
import { Form, Typography } from 'antd';
import map from 'lodash/map';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

export const ValidationEdit = () => {
    const [form] = Form.useForm()
    const { t } = useTranslation('translation', { keyPrefix: 'apiForm.validation' })
    const { validation, setValidation } = useCurlEditFormDataSelector()
    const [data, setData] = useState(addNanoid(validation))

    const columns = [
        {
            title: t('target'),
            dataIndex: 'target',
            width: '33%',
            editable: true,
            highlightedTextareaProps: {
                isHighlighted: true,
                initialVariables: VALIDATION_AUTOCOMPLETE_LIST,
                renderInBody: true
            },
            editableStyles: {
                maxWidth: '300px',
                width: '300px'
            },
            render: (value) => {
                const formatted = replaceWithReactNode(value,
                    (variable) => formatVariableToComponent(variable, variable, true))

                return <Typography.Text style={ { wordBreak: 'break-word' } }>{formatted}</Typography.Text>
            }
        },
        {
            title: t('validationType'),
            dataIndex: 'type',
            width: '33%',
            editable: true,
            inputType: 'select',
            selectOptions: arrayToOptions(VALIDATION_TYPES)
        },
        {
            title: t('expectedValue'),
            dataIndex: 'expectedValue',
            width: '33%',
            editable: true,
            style: {
                maxWidth: '300px',
                width: '300px'
            },
            render: (value) => {
                return <Typography.Text style={ { wordBreak: 'break-word' } }>{value}</Typography.Text>
            }
        },
    ]

    useEffect(() => {
        setValidation(map(data, (item) => ({
            target: item.target,
            type: item.type,
            expectedValue: item.expectedValue
        })))
    }, [data]);

    return (
        <EditableTable
            addText={ t('validation') }
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

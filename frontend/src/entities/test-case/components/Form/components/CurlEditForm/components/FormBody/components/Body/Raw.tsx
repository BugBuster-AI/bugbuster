import {
    TBodyRawType,
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { Select } from 'antd';
import TextArea from 'antd/lib/input/TextArea';

const options = [
    { label: 'Text', value: 'text' },
    { label: 'JavaScript', value: 'javascript' },
    { label: 'JSON', value: 'json' },
    { label: 'HTML', value: 'html' },
    { label: 'XML', value: 'xml' },
]

export const BodyRaw = () => {

    const { body, setBody } = useCurlEditFormDataSelector()

    const rawData = body?.raw

    const rawType = rawData?.type
    const rawValue = rawData?.value

    const handleChange = (value: string) => {
        setBody({
            raw: {
                value,
            }
        })
    }

    const handleChangeType = (type: TBodyRawType) => {
        setBody({
            raw: {
                type
            }
        })
    }

    return (
        <>
            <Select
                defaultValue={ 'text' }
                onChange={ handleChangeType }
                options={ options }
                style={ { marginBottom: 10, width: 120 } }
                value={ rawType }
                variant={ 'outlined' }
            />
            <TextArea
                cols={ 50 }
                onChange={ (e) => handleChange(e.target.value) }
                placeholder={ `JSON, XML, Form-Data \n{...`
                }
                rows={ 25 }
                style={ { height: '362px' } }
                value={ rawValue }
            />
        </>
    )
}

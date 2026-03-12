import {
    FormData
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/Body/FormData.tsx';
import {
    BodyRaw
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/Body/Raw.tsx';
import {
    UrlEncoded
} from '@Entities/test-case/components/Form/components/CurlEditForm/components/FormBody/components/Body/URLEncoded.tsx';
import {
    TBodyType,
    useCurlEditFormDataSelector
} from '@Entities/test-case/components/Form/components/CurlEditForm/context';
import { Flex, Radio } from 'antd';

const options = [
    { label: 'none', value: 'none' },
    { label: 'form-data', value: 'formData' },
    { label: 'x-www-form-urlencoded', value: 'urlEncoded' },
    { label: 'raw', value: 'raw' },
]

export const BodyEdit = () => {
    const { body, setBody } = useCurlEditFormDataSelector()

    const handleChangeType = (type: TBodyType) => {
        setBody({
            currentBodyType: type
        })
    }

    const currentBodyType = body.currentBodyType

    return (
        <Flex vertical>
            <Radio.Group
                defaultValue={ currentBodyType }
                onChange={ (e) => handleChangeType(e.target.value) }
                options={ options }
                style={ { marginBottom: 10 } }
                value={ currentBodyType }
            />

            <div>
                {currentBodyType === 'raw' && <BodyRaw/>}
                {currentBodyType === 'formData' && <FormData/>}
                {currentBodyType === 'urlEncoded' && <UrlEncoded/>}
            </div>
        </Flex>
    )
}

import { SearchOutlined } from '@ant-design/icons';
import { Input, InputProps } from 'antd';
import { useTranslation } from 'react-i18next';

interface IProps extends InputProps {

}

export const Search = ({ ...props }: IProps) => {
    const { t } = useTranslation()

    return (
        <Input
            placeholder={ t('common.input_search.placeholder') }
            style={ { width: '240px' } }
            suffix={ <SearchOutlined/> }
            allowClear
            { ...props }
        />
    )
}

import { SearchOutlined } from '@ant-design/icons';
import { useRecordsStore } from '@Entities/records/store';
import { Button, Input } from 'antd';
import { useTranslation } from 'react-i18next';

export const SearchRun = () => {
    const { t } = useTranslation()
    const setSearchValue = useRecordsStore((state) => state.setSearchValue)
    const searchValue = useRecordsStore((state) => state.searchValue)

    return (
        <Input.Search
            enterButton={ <Button icon={ <SearchOutlined /> } /> }
            onChange={ (e) => setSearchValue(e.target.value) }
            placeholder={ t('common.input_search.placeholder') }
            style={ { width: '240px' } }
            value={ searchValue }
            allowClear
        />
    )
}

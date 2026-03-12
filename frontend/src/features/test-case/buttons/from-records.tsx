import { PlusOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { Button } from 'antd';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

export const CreateFromRecords = () => {
    const { t } = useTranslation()
    const { id } = useParams()
    const navigate = useNavigate()

    const handleClick = () => {
        if (id) {
            navigate(PATHS.RECORDS.ABSOLUTE(id))
        }
    }

    return (
        <Button icon={ <PlusOutlined/> } onClick={ handleClick }>
            {t('repository_page.content.toolbar.case_btn')}
        </Button>
    )
}

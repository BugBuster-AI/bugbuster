import { PlusOutlined } from '@ant-design/icons';
import { PATHS } from '@Common/consts';
import { Button } from 'antd';
import { ReactElement, type MouseEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';

interface IProps {
    recordId: string
}

export const AddCaseButton = ({ recordId }: IProps): ReactElement => {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const { id } = useParams()

    const handleClick = (e: MouseEvent) => {
        e.stopPropagation()

        navigate(`${PATHS.REPOSITORY.CREATE_CASE.ABSOLUTE(id!)}?recordId=${recordId}`)
    }

    return (
        <Button
            color="primary"
            icon={ <PlusOutlined/> }
            onClick={ handleClick }
            size={ 'small' }
            variant="solid"
        >
            {t('common.case')}
        </Button>

    )
}

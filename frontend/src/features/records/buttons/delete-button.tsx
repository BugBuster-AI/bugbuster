import { DeleteOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { useDeleteHappypass } from '@Entities/records/queries/mutations.ts';
import { Typography } from 'antd';
import { ReactElement, MouseEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';

interface IProps {
    recordId: string
}

export const DeleteButton = ({ recordId }: IProps): ReactElement => {
    const { id } = useParams()
    const { mutateAsync } = useDeleteHappypass(id!)
    const { t } = useTranslation()
    const handleClick = async (e: MouseEvent) => {
        e.stopPropagation()
        await asyncHandler(mutateAsync.bind(null, recordId))
    }

    return (
        <ConfirmButton
            icon={ <DeleteOutlined/> }
            modalProps={ {
                maskClosable: true,
                destroyOnClose: true,
                centered: true,
                title: t('common.delete_title'),
                okText: t('common.ok'),
                cancelText: t('common.cancel'),
                onOk: handleClick
            } }
            closeAfterOk
        >
            <Typography.Text>{t('common.confirm_text')}</Typography.Text>
        </ConfirmButton>
    )
}

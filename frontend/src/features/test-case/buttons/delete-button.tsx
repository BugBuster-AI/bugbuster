import { DeleteOutlined } from '@ant-design/icons';
import { ConfirmButton } from '@Common/components';
import { asyncHandler } from '@Common/utils';
import { useDeleteTestCases } from '@Entities/test-case/queries';
import { Typography } from 'antd';
import isArray from 'lodash/isArray';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    case_id: string | string[]
    disabled?: boolean
    onClick?: () => void
}


export const DeleteButton = ({ case_id, disabled = false, onClick }: IProps): ReactElement => {
    const { t } = useTranslation()
    const { mutateAsync, isPending } = useDeleteTestCases()

    const handleClick = async () => {
        if (disabled) return

        if (isArray(case_id)) {
            onClick && onClick()
            await asyncHandler(mutateAsync.bind(null, case_id))
        }
    }

    return (
        <ConfirmButton
            buttonProps={ {
                disabled: disabled,
                type: 'default',
                loading: isPending
            } }
            icon={ <DeleteOutlined/> }
            modalProps={ {
                okButtonProps: {
                    loading: isPending
                },
                centered: true,
                title: t('common.delete_title'),
                onOk: handleClick,
                okText: t('common.confirm'),
                cancelText: t('common.cancel')
            } }
            closeAfterOk
        >
            <Typography.Text>{t('common.confirm_text')}</Typography.Text>
        </ConfirmButton>
    )
}

import { Flex, Modal, ModalProps, Typography } from 'antd';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    subtitle?: ReactNode
    toolbar?: ReactNode
    body?: ReactNode
    modalProps?: ModalProps
}
export const FromRecordsModal = ({ subtitle, toolbar, body, modalProps }: IProps) => {
    const { t } = useTranslation()

    return (
        <Modal
            cancelText={ t('create_case_records.button_cancel') }
            okText={ t('create_case_records.button_ok') }
            title={ t('create_case_records.title') }
            width={ 1080 }
            centered
            destroyOnClose
            { ...modalProps }
        >
            <Flex gap={ 16 } vertical>
                {subtitle || <Typography.Text>{t('create_case_records.subtitle')}</Typography.Text>}
                {toolbar}
                {body}
            </Flex>
        </Modal>
    )
}

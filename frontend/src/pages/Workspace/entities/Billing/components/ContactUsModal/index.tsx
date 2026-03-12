import { ContactUs } from '@Features/billing/contact-us';
import { Modal } from 'antd';
import { ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    renderTrigger?: ({ onClick, open }: { onClick: () => void, open: boolean }) => ReactNode
}

export const ContactUsModal = ({ renderTrigger }: IProps) => {
    const [open, setOpen] = useState(false)
    const { t } = useTranslation()

    const handleClose = () => {
        setOpen(false)
    }

    const handleOpen = () => {
        setOpen(true)
    }

    return <>
        {renderTrigger?.({ open, onClick: handleOpen })}
        <Modal
            footer={ null }
            onCancel={ handleClose }
            open={ open }
            title={ t('contactUs.title') }
            centered
            destroyOnClose
        >
            <ContactUs onFinish={ handleClose }/>
        </Modal>
    </>
}

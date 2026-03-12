import { Button, message, Modal } from 'antd';
import { useTranslation } from 'react-i18next';
import { ContextScreenshotIcon } from '../ContextScreenshotIcon';

interface IProps {
    onClick?: () => void
    needShowModal?: boolean
    isDeleted?: boolean
    screenshotUrl?: string
}

export const ContextScreenshotControl = ({ screenshotUrl, isDeleted, onClick, needShowModal }: IProps) => {
    const { t } = useTranslation()

    const handleClick = () => {
        if (needShowModal) {
            const modal = Modal.confirm({
                centered: true,
                closable: true,
                closeIcon: true,
                title: t('contextScreenshot.deleteTitle'),
                maskClosable: true,
                content: t('contextScreenshot.delete'),
                icon: null,
                onOk: async () => {
                    try {
                        onClick?.()
                        modal.destroy()
                    } catch {
                        message.error('Failed to delete context screenshot')
                    }
                }
            })

            return
        }

        onClick?.()
    }

    return (
        <Button
            icon={ 
                <ContextScreenshotIcon
                    delay={ 0.6 }
                    disabled={ isDeleted }
                    preview={ false }
                    screenshotUrl={ screenshotUrl }
                    styles={ { width: 16, height: 16 } }
                    wrapStyles={ { position: 'relative', inset: 0 } } 
                />
            }
            onClick={ handleClick }
            size="small"
            type="text"
            variant="text"
        />
    )
}

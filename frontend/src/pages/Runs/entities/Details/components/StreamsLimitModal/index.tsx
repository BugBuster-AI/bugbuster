import { CloseOutlined } from '@ant-design/icons';
import { Modal } from 'antd';
import parse from 'html-react-parser';
import { useTranslation } from 'react-i18next';

export const useStreamsLimitModal = () => {
    const { t } = useTranslation()
    const open = () => {
        Modal.info({
            centered: true,
            destroyOnClose: true,
            icon: null,
            closable: true,
            maskClosable: true,
            closeIcon: <CloseOutlined/>,
            title: t('no_streams_available.title'),
            content: parse(t('no_streams_available.content')),
        })
    }

    return { open }
}

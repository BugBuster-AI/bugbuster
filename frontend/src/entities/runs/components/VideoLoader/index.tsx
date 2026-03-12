import { LoadingOutlined } from '@ant-design/icons';
import { Flex, Spin, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

export const VideoLoader = () => {
    const { t } = useTranslation()
    const text = t('common.video_loading')

    return (
        <Flex align={ 'center' } gap={ 8 }>
            <Spin indicator={ <LoadingOutlined style={ { color: 'rgba(22, 119, 255, 1)' } }/> } spinning/>
            <Typography.Text type={ 'secondary' }>{text}</Typography.Text>
        </Flex>
    )
}

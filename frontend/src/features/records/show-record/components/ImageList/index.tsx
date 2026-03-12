import { useShowRecordStore } from '@Features/records/show-record/store';
import { Divider, Flex, Skeleton } from 'antd';
import map from 'lodash/map';
import { useTranslation } from 'react-i18next';

export const ImageList = () => {
    const { t } = useTranslation()
    const run = useShowRecordStore((state) => state.record)
    const setImage = useShowRecordStore((state) => state.setCurrentImage)
    const currentImg = useShowRecordStore((state) => state.currentImage)
    const loading = useShowRecordStore((state) => state.loading)
    const images = run?.images || []

    if (loading) return map(Array.from({ length: 2 }), () => (
        <Skeleton.Node
            style={ { height: '200px', width: '100%' } }
        />
    ))

    return (
        <Flex vertical>
            <Divider orientation={ 'left' } orientationMargin={ 0 } style={ { fontWeight: 800 } }>
                {t('show_record.screenshots')}
            </Divider>

            {map(images, (image, index) => {
                const isActive = index === currentImg

                return (
                    <div
                        onClick={ setImage.bind(null, index) }
                        style={ {
                            width: '100%',
                            borderRadius: '16px',
                            cursor: 'pointer',
                            padding: '4px',
                            border: `2px solid ${isActive ? 'black' : 'transparent'}` } }
                    >
                        <img
                            key={ `show-mini-img-${index}` }
                            src={ image.url }
                            style={ { objectFit: 'contain', width: '100%' } }
                        />
                    </div>
                )
            })}
        </Flex>
    )
}

import { useThemeToken } from '@Common/hooks';
import { useShowRecordStore } from '@Features/records/show-record/store';
import { Divider, Flex, Image, Typography } from 'antd';
import map from 'lodash/map';
import { useTranslation } from 'react-i18next';

export const ShowContent = () => {
    const token = useThemeToken()
    const record = useShowRecordStore((state) => state.record)
    const images = record?.images
    const { t } = useTranslation()

    return (
        <Flex
            style={ {
                overflow: 'auto',
                height: '100%',
                width: '100%',
                padding: '0 24px 16px 24px',
                borderLeft: `1px solid ${token.colorSplit}`
            } }
            vertical
        >
            <Divider orientation="left" orientationMargin={ 0 } style={ { margin: 0 } } plain>
                <Typography.Title level={ 5 } style={ { fontWeight: 800 } }>
                    {t('records.content.title')}
                </Typography.Title>
            </Divider>
            <Flex gap={ 2 } vertical>
                {map(images, (item) => (
                    <Image
                        preview={ {
                            destroyOnClose: true,
                            imageRender: () => (
                                <div
                                    style={ {
                                        backgroundColor: 'white',
                                        height: '100%',
                                        display: 'flex',
                                        alignItems: 'center'
                                    } }
                                >
                                    <img
                                        src={ item.url }
                                        width="100%"
                                    />
                                </div>
                            ),
                            toolbarRender: () => null,
                        } }
                        src={ item.url }
                        wrapperClassName={ 'image-with-hover' }
                    />
                ))
                }
            </Flex>

        </Flex>
    )
}

import { FieldTimeOutlined } from '@ant-design/icons';
import { DEFAULT_IMAGE_SIZE } from '@Common/consts';
import { useThemeToken } from '@Common/hooks';
import { isShowBeforeImage } from '@Entities/runs/utils/isShowBeforeImage';
import { ELocalStepItemVariant } from '@Entities/test-case/components/StepsView/StepItemView.tsx';
import { ILocalStepData } from '@Entities/test-case/models';
import { Flex, Image, Typography } from 'antd';
import isString from 'lodash/isString';
import map from 'lodash/map';
import size from 'lodash/size';
import { useTranslation } from 'react-i18next';

interface IProps {
    step: ILocalStepData
    variant?: ELocalStepItemVariant
}

export const DefaultStepDetails = ({ step, variant = ELocalStepItemVariant.SIMPLE }: IProps) => {
    const { t } = useTranslation()
    const token = useThemeToken()

    const {
        afterImage,
        beforeImage,
        completeTime,
        name,
        description,
        actionType,
        attachments,
    } = step || {}

    const getBeforeImageCaption = () => {
        const extra = step?.extra

        if (extra?.use_single_screenshot === true) {
            return t('resultVerifications.state')
        }

        if (extra?.use_single_screenshot === false) {
            return t('resultVerifications.dynamic')
        }

        return ''
    }

    const beforeImageCaption = getBeforeImageCaption()

    return <>
        {!!description && (
            isString(description)
                ? <Typography.Text style={ { color: token.colorTextDescription } }>
                    {description}
                </Typography.Text>
                : description
        )
        }

        {((actionType || completeTime) && variant === ELocalStepItemVariant.DETAILED) &&
            <Flex align="center" justify="space-between" style={ { width: '100%' } }>
                {
                    actionType
                        ? (
                            <Typography.Text style={ { color: token.colorTextDescription } }>
                                {actionType}
                            </Typography.Text>
                        )
                        : <div/>
                }

                <Flex align="center" gap={ 8 }>
                    <Typography.Text style={ { color: token.colorTextDescription } }>{name}</Typography.Text>
                    {!completeTime === false &&
                        (
                            <Typography.Text style={ { color: token.colorTextDescription } }>
                                <FieldTimeOutlined
                                    style={ { color: token.colorTextDescription, marginRight: '4px' } }
                                />
                                {completeTime || '0.00'}
                            </Typography.Text>
                        )}
                </Flex>
            </Flex>}

        {attachments && size(attachments) && (

            <Flex className={ 'log-card-images' } gap={ 4 } style={ { width: '100%', overflow: 'auto' } }>
                {map(attachments, (attachment, index) => (
                    <Image
                        key={ `${index}-${attachment.file}` }
                        src={ attachment?.url }
                        style={ {
                            objectFit: 'contain',
                            height: '100%',
                        } }
                        wrapperStyle={ {
                            height: DEFAULT_IMAGE_SIZE.SMALL.height,
                        } }
                    />

                ))}
            </Flex>

        )}


        {(!!afterImage || !! beforeImage) && (
            <Flex gap={ 12 } vertical>
                <Flex className={ 'log-card-images' } gap={ 16 }>
                    {isShowBeforeImage(step, beforeImage, true) && (
                        <Flex vertical>
                            <Typography.Text style={ { color: token.colorTextDescription } }>
                                {t('runs_history.before')}
                            </Typography.Text>
                            <Image src={ beforeImage!.url } wrapperStyle={ { aspectRatio: '277/150' } }/>
                        </Flex>
                    )}
                    {!!afterImage && (
                        <Flex vertical>
                            <Typography.Text style={ { color: token.colorTextDescription } }>
                                {t('runs_history.after')}
                            </Typography.Text>
                            <Image
                                src={ afterImage.url }
                                wrapperStyle={ { aspectRatio: '277/150' } }/>
                        </Flex>
                    )
                    }
                </Flex>
                <Typography.Text type="secondary">
                    {beforeImageCaption}
                </Typography.Text>
            </Flex>
        )}
    </>
}

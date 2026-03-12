import { FieldTimeOutlined } from '@ant-design/icons';
import { EStatusIndicator, StatusIndicator } from '@Common/components';
import { DEFAULT_IMAGE_SIZE } from '@Common/consts';
import { METHOD_COLORS } from '@Common/consts/common.ts';
import { useThemeToken } from '@Common/hooks';
import { formatVariableToComponent, replaceWithReactNode } from '@Common/utils/formatVariable.tsx';
import { IMedia } from '@Entities/runs/models';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { Flex, GlobalToken, Image, Typography } from 'antd';
import isObject from 'lodash/isObject';
import isString from 'lodash/isString';
import map from 'lodash/map';
import size from 'lodash/size';
import { ComponentProps, CSSProperties, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import stylesCSS from './styles.module.scss'

type TCardVariant = 'run' | 'history'

interface IProps {
    title: string;
    time?: string | false;
    description?: string | ReactNode
    status?: EStatusIndicator
    stepType?: EStepType
    actionName?: string;
    img?: string[],
    step?: string
    onClick?: () => void,
    countNumber?: number | string // Номер лога
    variant?: TCardVariant
    style?: CSSProperties
    noStatus?: boolean
    beforeImg?: string;
    disabled?: boolean;
    afterImg?: string;
    statusProps?: ComponentProps<typeof StatusIndicator>
    isLoading?: boolean,
    attachments?: IMedia[]
}

const getStyles = (variant: TCardVariant, token: GlobalToken) => {
    switch (variant) {
        case 'run':
            return {
                backgroundColor: token.colorFillAlter,
                padding: 16,
                width: '100%',
                borderRadius: token.sizeXS,
                border: `1px solid ${token.colorBorderSecondary}`,
                cursor: 'pointer'
            }
        default:
            return {}
    }
}

export const LogCard = ({
    time,
    onClick,
    status = EStatusIndicator.IDLE,
    countNumber,
    actionName,
    beforeImg,
    afterImg,
    isLoading,
    description,
    title,
    variant = 'run',
    noStatus = false,
    statusProps,
    style: overrideStyle,
    stepType,
    step,
    disabled,
    attachments
}: IProps) => {
    const token = useThemeToken()
    const { t } = useTranslation()
    const styles = getStyles(variant, token)

    const getActionNameStyles = (): CSSProperties => {
        switch (stepType) {
            case EStepType.API:
                return {
                    fontWeight: 'bold',
                    color: METHOD_COLORS?.[actionName?.toUpperCase() as keyof typeof METHOD_COLORS]
                        || token.colorTextDescription
                }
            default:
                return {
                    color: token.colorTextDescription
                }
        }
    }

    const handleClick = () => {
        if (disabled) return

        onClick && onClick()
    }

    const disabledStyles = disabled ? {
        opacity: 0.5,
        cursor: 'not-allowed'
    } : {}

    const formattedTitle = isObject(title) ? JSON.stringify(title) : replaceWithReactNode(title,
        (variable, index) => formatVariableToComponent(variable, index)
    )


    return (
        <Flex
            align="flex-start"
            gap={ 16 }
            onClick={ handleClick }
            style={ { width: '100%', height: 'fit-content', ...styles, ...overrideStyle, ...disabledStyles } }
        >
            {!noStatus && <StatusIndicator
                count={ countNumber }
                loading={ isLoading }
                status={ status }
                { ...statusProps }
            />}
            <Flex
                align="flex-start"
                flex={ 1 }
                gap={ 10 }
                justify="space-between"
                style={ { height: '100%', width: '100%', } }
                vertical
            >
                <Typography.Text className={ stylesCSS.title }>{formattedTitle}</Typography.Text>
                {!!description && (
                    isString(description)
                        ? <Typography.Text style={ { color: token.colorTextDescription } }>
                            {description}
                        </Typography.Text>
                        : description
                )
                }

                {(actionName || time || step) && <Flex
                    align="center"
                    justify="space-between"
                    style={ { width: '100%' } }
                >
                    {
                        actionName
                            ? (
                                <Typography.Text style={ { ...getActionNameStyles() } }>
                                    {actionName.toUpperCase()}
                                </Typography.Text>
                            )
                            : <div/>
                    }

                    <Flex align="center" gap={ 8 }>
                        <Typography.Text style={ { color: token.colorTextDescription } }>{step}</Typography.Text>
                        {!time === false && <Typography.Text style={ { color: token.colorTextDescription } }>
                            <FieldTimeOutlined style={ { color: token.colorTextDescription, marginRight: '4px' } }/>
                            {time || '0.00'}
                        </Typography.Text>}
                    </Flex>
                </Flex>
                }

                {attachments && size(attachments) && (

                    <Flex className={ 'log-card-images' } gap={ 4 } style={ { width: '100%', overflow: 'scroll' } }>
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

                {(!!beforeImg || !!afterImg) && (
                    <Flex className={ 'log-card-images' } gap={ 16 }>
                        {!!beforeImg && (
                            <Flex vertical>
                                <Typography.Text style={ { color: token.colorTextDescription } }>
                                    {t('runs_history.before')}
                                </Typography.Text>
                                <Image src={ beforeImg } wrapperStyle={ { aspectRatio: '277/150' } }/>
                            </Flex>
                        )}
                        {!!afterImg && (
                            <Flex vertical>
                                <Typography.Text style={ { color: token.colorTextDescription } }>
                                    {t('runs_history.after')}
                                </Typography.Text>
                                <Image
                                    src={ afterImg }
                                    wrapperStyle={ { aspectRatio: '277/150' } }/>
                            </Flex>
                        )
                        }
                    </Flex>
                )}
            </Flex>
        </Flex>
    )

}

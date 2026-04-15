import { FieldTimeOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ERunStatus } from '@Entities/runs/models';
import { getReflectionStatus } from '@Entities/runs/utils/getReflectionStatus';
import { ansiToReactNodes } from '@Features/test-case/playwright-codegen/codegenLogAnsi';
import { Flex, Typography } from 'antd';
import cn from 'classnames';
import parse from 'html-react-parser';
import isUndefined from 'lodash/isUndefined';
import { memo, CSSProperties, type ReactNode, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { OverflowContainer } from '../OverflowContainer';
import { StatusIndicator } from '../StatusIndicator';
import styles from './ResultCard.module.scss'

export type TResultTextFormat = 'html' | 'ansi'

interface IProps {
    status: ERunStatus | boolean
    result?: string | null
    /**
     * По умолчанию html (как раньше через html-react-parser).
     * ansi — для логов/ошибок Playwright с ESC-последовательностями.
     */
    resultFormat?: TResultTextFormat
    time?: string
    helperText?: string
    needIcon?: boolean
    size?: 'small' | 'medium'
    title?: string
}

const MAX_HEIGHT = 142

function renderResultBody (value: string | ReactNode, format: TResultTextFormat): ReactNode {
    if (typeof value !== 'string') {
        return value;
    }
    if (format === 'ansi') {
        return ansiToReactNodes(value);
    }

    return parse(value);
}

export const ResultContent = memo((
    { value, bgColor, style, showMoreBtnStyle, format = 'html' }:
     {
         value?: string | ReactNode | null;
         bgColor?: string;
         style?: CSSProperties;
         showMoreBtnStyle?: CSSProperties;
         format?: TResultTextFormat;
     }
) => {
    const [isOpened, setIsOpened] = useState(false);

    if (value == null || value === '') {
        return null;
    }

    const handleOpen = () => {
        setIsOpened(!isOpened)
    }

    const overflowText = isOpened ? 'Show less' : 'Show more';
    
    return (
        <OverflowContainer>
            {({ isOverflow, originalHeight }) => {
                const hasOverflow = (originalHeight ?? 0) > MAX_HEIGHT;
                const maxHeight = isOpened ? (originalHeight ?? 0 ) + 610 : MAX_HEIGHT;
                const transitionDuration = .3;

                return (
                    <Typography.Text
                        className={ cn(styles.resultText, { [styles.isOverflow]: isOverflow && !isOpened }) }
                        style={ { 
                            ...style,
                            '--result-bg-color': bgColor || 'white',
                            whiteSpace: 'pre-line',
                            maxHeight: maxHeight, 
                            transition: `${transitionDuration}s ease`,
                        } as CSSProperties 
                        }
                    >
                        {renderResultBody(value, format)}
                        {(hasOverflow || isOpened) && (
                            <p className={ styles.moreBtn } onClick={ handleOpen } style={ showMoreBtnStyle }>
                                {overflowText}
                            </p>
                        )}
                    </Typography.Text>
                )
            }}
        </OverflowContainer>
    )
})


export const ResultCard = ({
    status,
    title,
    size = 'small',
    needIcon,
    result,
    resultFormat = 'html',
    time,
    helperText,
}: IProps) => {
    const token = useThemeToken()

    const getColors = () => {
        switch (status) {
            case false:
            case ERunStatus.FAILED:
                return {
                    color: token.colorErrorText,
                    border: `1px solid ${token.colorErrorBorder}`,
                    backgroundColor: token.colorErrorBg
                }
            case true:
            case ERunStatus.PASSED:
                return {
                    color: token.colorSuccessText,
                    border: `1px solid ${token.colorSuccessBorder}`,
                    backgroundColor: token.colorSuccessBg
                }
            case ERunStatus.AFTER_STEP_FAILURE:
                return {
                    color: token.colorWarningText,
                    border: `1px solid ${token.colorWarningBorder}`,
                    backgroundColor: token.colorWarningBg
                }
            default:
                return {
                    color: token.colorText,
                    border: `1px solid ${token.colorBorder}`,
                    backgroundColor: token.colorBgLayout
                }
        }

    }

    const { color, backgroundColor, border } = getColors()
    const { t } = useTranslation()

   
    const paddings = {
        small: '16px',
        medium: '20px 24px'
    }

    const resultTime = time ? Number(time) : 0

    return (
        <Flex
            gap={ result ? 8 : 0 }
            justify="space-between"
            style={ {
                width: '100%',
                backgroundColor,
                border,
                color,
                padding: paddings[size],
                borderRadius: '8px',
            } }
            vertical
        >

            <Flex gap={ needIcon ? 16 : 0 }>
                {needIcon && <StatusIndicator status={ getReflectionStatus(status) }/>}

                <Flex gap={ 8 } vertical>
                    {!!helperText && <Typography.Text strong>
                        {helperText}
                    </Typography.Text>
                    }
                    {!!title && <Typography.Text>
                        {title}
                    </Typography.Text>
                    }
                    <ResultContent bgColor={ backgroundColor } format={ resultFormat } value={ result } />
                </Flex>
            </Flex>

            {!isUndefined(time) && (
                <Flex justify={ 'space-between' } style={ { width: '100%', paddingLeft: needIcon ? 40 : 0 } }>
                    <Typography.Text>{t('running_page.total_time')}</Typography.Text>
                    <Typography.Text>
                        <FieldTimeOutlined style={ { marginRight: '8px' } }/>

                        {isNaN(resultTime) ? time : formatSeconds(Number(time || 0), t)}
                    </Typography.Text>
                </Flex>
            )}
        </Flex>
    )
}

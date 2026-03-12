import VectorIcon from '@Assets/icons/vector-square.svg?react';
import { Flex, Image, Tooltip, Typography } from 'antd'
import { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next';
import stylesCSS from './ContextScreenshotIcon.module.scss'

interface IProps {
    disabled?: boolean
    screenshotUrl?: string
    styles?: CSSProperties
    wrapStyles?: CSSProperties
    preview?: boolean
    delay?: number
}
export const ContextScreenshotIcon = ({ 
    delay, preview = true, styles, screenshotUrl,wrapStyles, disabled }: IProps) => {
    const { t } = useTranslation()

    return <Tooltip
        className={ stylesCSS.contextTooltip }
        mouseEnterDelay={ delay }
        open={ disabled ? false : undefined }
        rootClassName={ stylesCSS.contextTooltipRoot }
        title={ ( 
            <Flex gap={ 6 } onClick={ (e) => e.stopPropagation() } style={ { width: 400, padding: 8 } } vertical>
                <Typography style={ { color: 'white' } }>{t('contextScreenshot.stepUse')}</Typography>
                {screenshotUrl && (
                    <Image
                        className={ stylesCSS.contextScreenshotImage }
                        onClick={ (e) => e.stopPropagation() }
                        preview={ preview }
                        src={ screenshotUrl }
                    />
                )}
            </Flex> 
        ) }
    >
        <div className={ stylesCSS.contextIconWrapper } style={ wrapStyles }>
            <VectorIcon style={ { opacity: disabled ? 0.35 : 1, ...styles } } />
        </div>
    </Tooltip>
}

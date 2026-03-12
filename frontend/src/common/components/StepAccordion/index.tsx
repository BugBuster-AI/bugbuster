import { useThemeToken } from '@Common/hooks';
import { Collapse, Divider, Typography } from 'antd';
import { ItemType } from 'rc-collapse/es/interface';
import { CSSProperties, Key, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    key?: Key
    style?: CSSProperties
    label?: string
    defaultOpened?: boolean
    children?: ReactNode
}

export const EmptyStep = () => {
    const { t } = useTranslation()
    const token = useThemeToken()

    return (
        <Typography.Text style={ { color: token.colorTextDescription } }>
            {t('common.no_steps')}
        </Typography.Text>
    )
}

export const StepAccordion = ({ label, children, style, key, defaultOpened = true }: IProps) => {
    const itemKey = `step-accordion-${key}-${label}`

    const item: ItemType = {
        key: itemKey,
        label: (
            <Divider orientation={ 'left' } orientationMargin={ 0 } style={ { fontWeight: 'bold', margin: 0 } }>
                {label}
            </Divider>
        ),
        styles: {
            header: {
                paddingBlock: '8px',
                alignItems: 'center',
                paddingInline: 0,
            },
            body: {
                paddingInline: 0,
                paddingBlock: '8px'
            }
        },
        children: children || <EmptyStep/>
    }

    return <Collapse

        defaultActiveKey={ defaultOpened ? [itemKey] : undefined }
        items={ [item] }
        style={ style }
        // collapsible="header"
        ghost
    />
}

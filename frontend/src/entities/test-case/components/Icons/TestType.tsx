import Icon from '@ant-design/icons';
import Automated from '@Assets/icons/automated_test.svg?react'
import Manual from '@Assets/icons/manual_test.svg?react';
import { ETestCaseType } from '@Entities/test-case/models';
import { Tooltip } from 'antd';
import { ComponentProps, CSSProperties, memo, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps extends ComponentProps<typeof Icon> {
    iconStyles?: CSSProperties
}

export const AutomatedTest = ({ iconStyles, ...props }: IProps) => {

    return <Icon { ...props } component={ () => <Automated style={ { ...iconStyles } }/> }/>
}

export const ManualTest = ({ iconStyles, ...props }: IProps) => {

    return <Icon { ...props } component={ () => <Manual style={ { ...iconStyles } }/> }/>
}

export const TestTypeIcon = memo(({ type, style }: { type?: ETestCaseType, style?: CSSProperties }) => {
    let icon: ReactNode | null = null
    const { t } = useTranslation()

    switch (type) {
        case ETestCaseType.automated:
            icon = <AutomatedTest/>
            break
        default:
            icon = <ManualTest/>
            break
    }

    const title = `${t('caseTypes.index')} ${t(`caseTypes.${type}`)}`

    return (
        <Tooltip title={ title }>
            <div style={ { display: 'flex', justifyContent: 'center', ...style } }>
                {icon}
            </div>
        </Tooltip>
    )
})

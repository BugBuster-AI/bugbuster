import Icon, { SettingOutlined } from '@ant-design/icons';
import YellowLamp from '@Assets/icons/expected-result/yellow1.svg?react'
import SharedStepIcon from '@Assets/icons/shared-step/icon.svg?react'
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { Flex } from 'antd';
import { CSSProperties, ReactNode } from 'react';

interface IProps {
    stepType: EStepType,
    isSharedStep?: boolean
    isExpected?: boolean
    style?: CSSProperties
    size?: 'small' | 'large'
    variant?: 'circle' | 'raw'
}

export const getStepIcon = ({ stepType, isExpected, isSharedStep, variant = 'circle', style }: IProps) => {
    let rawIcon: ReactNode | null = null
    const needCircle = stepType !== EStepType.RESULT

    if (isSharedStep) {
        rawIcon = <SharedStepIcon style={ { color: 'white', width: '11px', height: '11px', ...style } }/>
    } else if (isExpected) {
        rawIcon =
            <Icon component={ () => <YellowLamp style={ { width: '14px', height: '14px', ...style } }/> }/>
    } else {
        switch (stepType) {
            case EStepType.SHARED_STEP:
                rawIcon = <SharedStepIcon style={ { color: 'white', width: '11px', height: '11px', ...style } }/>
                break
            case EStepType.RESULT:
                rawIcon =
                    <Icon component={ () => <YellowLamp style={ { width: '14px', height: '14px', ...style } }/> }/>
                break
            case EStepType.API:
                rawIcon = <SettingOutlined style={ { minWidth: 8, minHeight: 8, fontSize: 8, color: 'white' } }/>
                break
        }
    }

    if (!rawIcon) {
        return null
    }

    if (variant === 'circle') {
        return <Flex
            align={ 'center' }
            justify={ 'center' }
            style={ needCircle ? {
                backgroundColor: 'black',
                padding: 3,
                width: 15.5,
                display: 'flex!important',
                height: 16,
                border: `1px solid white`,
                borderRadius: '50%'
            } : undefined }>
            {rawIcon}
        </Flex>
    }

    return rawIcon

}

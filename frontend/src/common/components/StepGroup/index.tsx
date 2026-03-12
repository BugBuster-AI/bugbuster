import { StatusIndicator } from '@Common/components';
import { Divider, Flex, Spin, Steps, Typography } from 'antd';
import compact from 'lodash/compact';
import isEmpty from 'lodash/isEmpty';
import { ComponentProps, ReactNode } from 'react';


interface IProps {
    label?: string
    children?: ReactNode
    noLabel?: boolean
    loading?: boolean
}

const StepGroup = ({ label, children, loading = false, noLabel = false }: IProps) => {

    if (!children || isEmpty(compact(children as []))) return null

    return (
        <Spin spinning={ loading }>
            <Flex align={ 'flex-start' } vertical>
                {!noLabel && <Divider orientation="left" orientationMargin={ 0 } style={ { marginBlock: '4px 12px' } } plain>
                    <Typography.Title level={ 5 }>
                        {label}
                    </Typography.Title>
                </Divider>}

                <Steps direction={ 'vertical' } size={ 'small' }>
                    {!loading && children}
                </Steps>
            </Flex>
        </Spin>
    )

}


interface IItemProps {
    title?: ReactNode
    statusProps?: ComponentProps<typeof StatusIndicator>
}

StepGroup.Item = ({ title, statusProps }: IItemProps) => {
    return (
        <Steps.Step
            icon={
                <StatusIndicator
                    badgeStyle={ { display: 'inline' } }
                    className={ 'step-indicator' }
                    { ...statusProps }
                />
            }
            title={ title }
        />
    )
}

export { StepGroup }

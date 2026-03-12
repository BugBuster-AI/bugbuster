import { ClockCircleOutlined } from '@ant-design/icons';
import { Flex, FlexProps, Typography, TypographyProps } from 'antd';
import { ReactNode } from 'react';

interface IProps {
    icon?: ReactNode
    wrapperProps?: Omit<FlexProps, 'children'>
    textProps?: TypographyProps;
    children?: ReactNode
}

export const TextWithIcon = ({ icon = <ClockCircleOutlined />, textProps, wrapperProps, children }: IProps) => {

    return (
        <Flex align={ 'center' } gap={ 8 } { ...wrapperProps }>
            {icon}
            <Typography.Text style={ { whiteSpace: 'nowrap' } } { ...textProps }>{children}</Typography.Text>
        </Flex>
    )
}

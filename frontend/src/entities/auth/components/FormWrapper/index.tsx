import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import { ReactElement, ReactNode } from 'react';

interface IProps {
    label: string;
    children?: ReactNode
    subtitle?: ReactNode
}

export const FormWrapper = ({ label, children, subtitle }: IProps): ReactElement => {
    const token = useThemeToken()

    return (
        <Flex
            style={ {
                width: '464px',
                padding: token.paddingXL,
                backgroundColor: token.colorFillTertiary,
                borderRadius: token.borderRadiusLG
            } }
            vertical
        >
            <div style={ { marginBottom: '40px', display: 'flex', flexDirection: 'column', gap: '12px' } }>
                <Typography.Title level={ 2 }>{label}</Typography.Title>
                {subtitle}
            </div>

            {children}
        </Flex>
    )
}

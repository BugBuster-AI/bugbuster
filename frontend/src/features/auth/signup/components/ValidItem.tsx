import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { Flex, Typography } from 'antd';
import { ReactElement } from 'react';



interface IProps {
    label: string
    isValid?: boolean
}

export const ValidItem = ({ isValid, label }: IProps): ReactElement => {
    const token = useThemeToken()
    const SuccessIcon = <CheckCircleOutlined style={ { color: token.colorSuccess } } />
    const ErrorIcon = <CloseCircleOutlined style={ { color: token.colorTextDescription } } />

    return (
        <Flex align={ 'center' } gap={ 8 }>
            {isValid ? SuccessIcon : ErrorIcon}
            <Typography.Text style={ { fontSize: '12px' } } type={ 'secondary' }>{label}</Typography.Text>
        </Flex>
    )
}

import { useThemeToken } from '@Common/hooks';
import { Col, Flex, Row, Typography } from 'antd';
import { ReactNode } from 'react';

interface IProps {
    title: string;

}

interface IProps {
    title: string
    children?: ReactNode
    bottomSlot?: ReactNode
}

const BillingInfoCard = ({ title, bottomSlot, children }: IProps) => {
    const token = useThemeToken()

    return (
        <Flex
            align={ 'flex-start' }
            gap={ 16 }
            style={ { padding: 16, borderRadius: 8, width: 480, border: `1px solid ${token.colorBorder}` } }
            vertical>
            <Typography.Title level={ 5 } style={ { margin: 0 } }>{title}</Typography.Title>
            {children}
            {bottomSlot}
        </Flex>
    )
}

interface IRowProps {
    name: ReactNode;
    content: ReactNode
}

BillingInfoCard.Row = ({ content, name }: IRowProps) => {
    const token = useThemeToken()

    return (
        <Row align={ 'middle' } style={ { width: '100%' } }>
            <Col span={ 9 } style={ { marginRight: 16 } }><Typography
                style={ { color: token.colorTextDescription } }>{name}</Typography></Col>
            <Col span={ 100 }>{content}</Col>
        </Row>
    )
}

export { BillingInfoCard }

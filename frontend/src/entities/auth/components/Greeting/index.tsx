import { useThemeToken } from '@Common/hooks';
import { Col, ColProps, Flex, Typography } from 'antd';
import { ReactNode } from 'react';

export interface IGreetingProps {
    logo?: ReactNode
    title?: string;
    description?: string;
    textColor?: string
    bg?: string
}

interface IProps extends ColProps, IGreetingProps {
}


export const Greeting = ({ style, textColor, logo, bg, title, description, ...props }: IProps) => {
    const token = useThemeToken()

    return (
        <Col
            style={ {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundImage: `url(${bg})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                ...style
            } }
            { ...props }
        >
            <Flex align={ 'center' } gap={ 32 } justify={ 'center' } style={ { maxWidth: 560 } } vertical>

                {logo}

                <Typography.Title
                    level={ 1 }
                    style={ {
                        textAlign: 'center',
                        margin: 0,
                        color: textColor || token.colorTextLightSolid,
                        fontWeight: 700
                    } }
                >
                    {title}
                </Typography.Title>
                <Typography.Text
                    style={ {
                        fontSize: '16px',
                        textAlign: 'center',
                        color: textColor || token.colorTextLightSolid,
                        margin: 0,
                    } }
                >
                    {description}
                </Typography.Text>
            </Flex>
        </Col>
    )
}

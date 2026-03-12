import { Flex, Typography } from 'antd';
import isObject from 'lodash/isObject';
import { ReactNode } from 'react';

interface IProps {
    title: string;
    children?: string | ReactNode
    content?: string
    first?: boolean
    className?: string
    contentClass?: string
}

export const InfoBlock = ({ children, contentClass, title, className, first, content }: IProps) => {

    if (!children && !content) {
        return null
    }

    const styles = first ? {
        marginBlock: 32
    } : {
        marginTop: 32
    }

    return (
        <Flex className={ className } gap={ 4 } style={ styles } vertical>
            <Typography.Title level={ 5 } style={ { margin: 0 } }>
                {isObject(title) ? JSON.stringify(title) : title}
            </Typography.Title>
            {children ? children : <Typography
                className={ contentClass }>{isObject(content) ? JSON.stringify(content) : content}</Typography>}
        </Flex>
    )
}

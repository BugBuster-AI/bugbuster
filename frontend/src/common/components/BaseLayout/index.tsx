import { Flex, Layout, Skeleton, Space, theme } from 'antd';
import { ComponentProps, ReactElement } from 'react';

const { useToken } = theme

type Props = ComponentProps<typeof Layout> & {
    loading?: boolean
}

export const BaseLayout = ({ children, loading, style, ...props }: Props): ReactElement => {
    const { token } = useToken()

    return (
        <Layout
            style={ {
                background: token.colorBgBase,
                padding: `${token.padding}px ${token.paddingXL}px`,
                ...style
            } }
            { ...props }>
            {loading ? <Skeleton paragraph={ { rows: 4 } }/> : children}
        </Layout>
    )
}

type TSpaceProps = ComponentProps<typeof Space>

export const BaseSpace = ({ children, style, ...props }: TSpaceProps): ReactElement => {
    const { token } = useToken()

    return (
        <Space
            style={ {
                background: token.colorBgBase,
                padding: `${token.padding}px ${token.paddingXL}px`,
                ...style
            } }
            { ...props }>
            {children}
        </Space>
    )
}

type TFlexProps = ComponentProps<typeof Flex> & {
    loading?: boolean
}

export const BaseFlex = ({ children, loading, style, ...props }: TFlexProps): ReactElement => {
    const { token } = useToken()

    return (
        <Flex
            style={ {
                background: token.colorBgBase,
                padding: `${token.padding}px ${token.paddingXL}px`,
                ...style
            } }
            { ...props }>
            {loading ? <Skeleton.Button/> : children}
        </Flex>
    )
}

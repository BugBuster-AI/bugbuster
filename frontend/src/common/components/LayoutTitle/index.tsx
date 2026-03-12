import { ArrowLeftOutlined } from '@ant-design/icons';
import { Button, Flex, Skeleton, theme, Typography } from 'antd';
import { CSSProperties, ReactElement, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

interface IProps {
    title?: string | ReactNode;
    withBack?: boolean
    info?: ReactNode
    backPath?: string
    renderTitle?: ReactNode
    extra?: ReactNode
    style?: CSSProperties
    loading?: boolean
}

const { useToken } = theme

export const LayoutTitle = ({ withBack, loading, title, info, backPath, extra, style }: IProps): ReactElement => {
    const navigate = useNavigate()
    const { token } = useToken()
    const handleBack = (): void => {
        backPath ? navigate(backPath) : navigate(-1)
    }

    return (
        <Flex
            align={ 'center' }
            gap={ token.margin }
            style={ {
                background: token.colorBgBase,
                padding: `${token.padding}px ${token.paddingXL}px`,
                ...style
            } }>
            {loading ? <Skeleton.Input/> : <>

                {withBack && <Button icon={ <ArrowLeftOutlined/> } onClick={ handleBack } type="text"/>}

                {typeof title === 'string' ?
                    (
                        <Typography.Title level={ 4 } style={ { margin: 0, wordBreak: 'keep-all' } }>
                            {title}
                        </Typography.Title>
                    ) : title
                }

                {info && (
                    <div style={ { alignSelf: 'flex-end' } }>
                        {info}
                    </div>
                )}

                {extra}
            </>}
        </Flex>
    )
}

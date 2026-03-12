import { Button, Flex } from 'antd';
import map from 'lodash/map';
import { ComponentProps, ReactElement } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

interface INavItem {
    path: string;
    label: string
    disabled?: boolean
}

interface IProps {
    items: INavItem[]
}

export const Navigation = ({ items }: IProps): ReactElement => {
    const navigate = useNavigate()
    const { pathname } = useLocation()
    const clickHandler = (path: string): void => {
        navigate(path)
    }

    const getButtonStyle = (isActive: boolean): Partial<ComponentProps<typeof Button>> => {
        if (isActive) {
            return {
                variant: 'filled',
                color: 'blue'
            }
        }

        return {
            color: 'default',
            variant: 'text'
        }
    }

    return (
        <Flex gap={ 8 }>
            {map(items, (item, index) => {
                const { path, label } = item || {}
                const isActive = pathname === path || (path !== '/' && pathname.startsWith(path))

                return (
                    <Button
                        key={ `navigationItem-${index}` }
                        disabled={ item.disabled }
                        onClick={ clickHandler.bind(null, path) }
                        { ...getButtonStyle(isActive) }
                    >
                        {label}
                    </Button>
                )
            })}
        </Flex>
    )
}

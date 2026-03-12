import { Col, Divider, Flex, Menu, MenuProps } from 'antd';
import { ReactNode } from 'react';

interface IProps {
    items: MenuProps['items']
    bottom?: ReactNode
    top?: ReactNode
}

export const SideBarView = ({ items, bottom, top }: IProps) => {

    return (
        <Flex align="stretch" justify="space-between" style={ { height: '100%' } } vertical={ true }>
            <Col>
                {Boolean(top) &&
                    <>
                        {top}
                        <Divider style={ { margin: '8px 0' } }/>
                    </>
                }

                <Menu
                    className="nav_menu"
                    items={ items }
                    mode="inline"
                    selectable={ false }
                    style={ {
                        background: 'transparent',
                        borderInlineEnd: 'none'
                    } }
                    theme="light"
                />
            </Col>
            <Col>
                {bottom}
            </Col>
        </Flex>
    )
}

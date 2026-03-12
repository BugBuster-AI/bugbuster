import { BellOutlined, UserOutlined } from '@ant-design/icons';
import BookIcon from '@Assets/icons/book.svg?react';
import HeaderLogo from '@Assets/icons/header-logo.svg?react';
import ScreenmateLogo from '@Assets/icons/screenmate_logo.svg?react';
import { PATHS } from '@Common/consts';
import { SHOW_ELEMENTS } from '@Common/consts/elements';
import { VERSION } from '@Common/consts/env.ts';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { HeaderUpgradeButton } from '@Entities/billing/components/HeaderUpgradeButton';
import { Row, Col, Space, Button, Avatar, theme } from 'antd';
import { Header } from 'antd/es/layout/layout';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigation } from './components/Navigation';

const { useToken } = theme;

interface IProps {
    renderAvatar?: ReactNode
}

export const PageHeader = ({ renderAvatar }: IProps): ReactElement => {
    const { token } = useToken();
    const { t } = useTranslation()
    const version = VERSION

    const user = useAuthStore((state) => state.user)
    const navigationItems = [
        {
            label: t('header.projects'),
            path: PATHS.INDEX
        },
        {
            label: t('header.workspace'),
            path: PATHS.WORKSPACE.USERS.ABSOLUTE,
            disabled: !user?.active_workspace_id
        }
    ]

    const handleDocumentationClick = () => {
        window.open('https://docs.bug-buster.ru/rukovodstvo-polzovatelya/chto-takoe-bugbuster', '_blank')
    }

    const logo = version === 'ru' ?
        <HeaderLogo style={ { width: 'auto', height: '100%' } }/> :
        <ScreenmateLogo style={ { height: 24, width: 'auto' } }/>;

    return (
        <Header
            style={ {
                borderBottom: `${token.lineWidth}px solid ${token.colorBorder}`,
            } }
        >
            <Row align="middle" justify="space-between">
                <Col>
                    <Space align="center" size="large">
                        {logo}
                        <Navigation items={ navigationItems }/>
                    </Space>
                </Col>

                <Col>
                    <Space align="center" size="middle">
                        {/* TODO: нужен рефач, вынести в отдельный модуль */}
                        { SHOW_ELEMENTS.BILLING.HEADER_PLAN && <HeaderUpgradeButton/>}
                        <Button color="default" icon={ <BellOutlined/> } size="large" variant="text"/>
                        <Button
                            color={ 'default' }
                            icon={ <BookIcon/> }
                            onClick={ handleDocumentationClick }
                            size={ 'large' }
                            variant={ 'text' }
                        />
                        {renderAvatar || (
                            <Avatar icon={ <UserOutlined/> }/>
                        )}
                    </Space>
                </Col>
            </Row>
        </Header>
    )
}


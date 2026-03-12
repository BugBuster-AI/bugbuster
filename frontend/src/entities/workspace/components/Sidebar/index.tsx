import { ExceptionOutlined, KeyOutlined, UserOutlined, WalletOutlined } from '@ant-design/icons';
import { BILLING_ROLES, LOGS_ROLES, PATHS } from '@Common/consts';
import { SHOW_ELEMENTS } from '@Common/consts/elements';
import { useThemeToken } from '@Common/hooks';
import { SideBarView } from '@Common/layouts';
import { useAuthStore } from '@Entities/auth/store/auth.store';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { Button, Flex, MenuProps, Skeleton, Typography } from 'antd';
import compact from 'lodash/compact';
import includes from 'lodash/includes';
import { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router-dom';

type MenuItem = Required<MenuProps>['items'][number];

const isLoading = false

interface IProps {
    editSlot?: ReactNode
    loading?: boolean
    tariffSlot?: ReactNode
}

export const WorkspaceSidebar = ({ editSlot, loading, tariffSlot }: IProps) => {
    const { t } = useTranslation()
    const token = useThemeToken()
    const logout = useAuthStore.use.logout()
    const workspace = useWorkspaceStore((state) => state.workspace)

    function getItem (
        label: ReactNode,
        key: string,
        icon?: ReactNode
    ): MenuItem {
        return {
            key,
            label: <NavLink to={ key }>{t(`workspace.sidebar.${label}`)}</NavLink>,
            icon
        } as MenuItem;
    }

    const items: MenuItem[] = [
        getItem('users', PATHS.WORKSPACE.USERS.ABSOLUTE, <UserOutlined/>),
        getItem('api_keys', PATHS.WORKSPACE.API_KEYS.ABSOLUTE, <KeyOutlined/>),
        (workspace && includes(LOGS_ROLES, workspace?.role))
            ? getItem('logs', `${PATHS.WORKSPACE.LOGS.ABSOLUTE}`,
                <ExceptionOutlined/>)
            : null,
        (workspace &&  SHOW_ELEMENTS.BILLING.WORKSPACE_PAGE && includes(BILLING_ROLES, workspace?.role))
            ? getItem('billing', `${PATHS.WORKSPACE.BILLING.ABSOLUTE}`,
                <WalletOutlined/>)
            : null
    ]

    const handleLogout = (): void => {
        logout()
    }

    return (
        <SideBarView
            bottom={
                <Flex gap={ 16 } vertical>
                    {tariffSlot}
                    <Button onClick={ handleLogout } style={ { width: 'fit-content' } }>
                        {t('menu.side.sign_out')}
                    </Button>
                </Flex>
            }
            items={ compact(items) }
            top={ isLoading ? <Skeleton.Input style={ { height: '16.5px' } }/> : (
                <Flex
                    align={ 'center' }
                    justify={ 'space-between' }
                    style={ {
                        width: '100%',
                        paddingLeft: '4px',
                        paddingRight: '4px',
                    } }>
                    {loading ?
                        <Skeleton.Input/> :
                        <Typography.Text
                            style={ {
                                fontWeight: 700,
                                paddingInline: token.paddingContentHorizontalLG
                            } }
                            strong>
                            {workspace?.workspace_name}
                        </Typography.Text>
                    }
                    {editSlot}
                </Flex>
            ) }
        />
    )
}

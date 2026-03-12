import { LoadingOutlined, UserOutlined } from '@ant-design/icons';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { workspaceQueries } from '@Entities/workspace/queries';
import { useChangeWorkspace } from '@Entities/workspace/queries/mutations.ts';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { useQuery } from '@tanstack/react-query';
import { Avatar, MenuProps, Dropdown, Space, Skeleton, message } from 'antd';
import map from 'lodash/map';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

export const AvatarDropdown = () => {
    const { t } = useTranslation()
    const getUser = useAuthStore((state) => state.getUser)
    const { data, refetch, isLoading } = useQuery({ ...workspaceQueries.list(), enabled: false })
    const navigate = useNavigate()
    const workspace = useWorkspaceStore((state) => state.workspace)
    const logout = useAuthStore((state) => state.logout)
    const { mutateAsync, isPending } = useChangeWorkspace()
    const [picture, setPicture] = useState(localStorage.getItem('user-picture'))

    const items: MenuProps['items'] = [
        {
            style: { width: '220px' },
            key: '2',
            label: t('header.dropdown.workspaces'),
            onTitleMouseEnter: () => refetch(),
            children: isLoading ? [
                {
                    key: 'loading',
                    label: <Skeleton.Input style={ { width: '100%' } }/>,
                    style: {
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 220
                    }
                }
            ] : map(data, (item) => ({
                key: item.workspace_id,
                disabled: !item?.workspace_id,
                onClick: async () => {
                    if (item?.workspace_id) {
                        if (workspace?.workspace_id === item.workspace_id) {
                            message.warning(t('messages.warning.common.currentWorkspaceId'))

                            return
                        }
                        try {
                            await mutateAsync(item?.workspace_id)
                            await getUser()
                            navigate('/')
                        } catch (e) {
                            message.error('Failed to fetch')
                            console.error('Failed to change workspace', e)
                        }
                    }
                },
                label: item.workspace_name,
                icon: isPending ? <LoadingOutlined/> : undefined,
                style: {
                    width: 220,
                    background: workspace?.workspace_id === item.workspace_id ? '#e6f7ff' : 'transparent',
                }
            }))

        },
        {
            key: 'divider',
            type: 'divider',
            style: {
                marginBlock: 10,
                marginInline: 'auto',
                width: '90%'
            }
        },
        {
            key: '3',
            label: t('header.dropdown.sign_out'),
            onClick: () => logout()
        },
    ];

    const pictureSrc = localStorage.getItem('user-picture');

    useEffect(() => {
        setPicture(pictureSrc)
    }, [pictureSrc])

    return <Dropdown menu={ { items } } trigger={ ['click'] } destroyPopupOnHide>
        <a onClick={ (e) => e.preventDefault() }>
            <Space>
                <Avatar icon={ <UserOutlined/> } src={ picture }/>
            </Space>
        </a>
    </Dropdown>
};


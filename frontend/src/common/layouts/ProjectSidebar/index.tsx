import {
    AppstoreAddOutlined,
    FolderOpenOutlined,
    PlayCircleOutlined,
    VideoCameraOutlined,
} from '@ant-design/icons';
import BracketsIcon from '@Assets/icons/brackets.svg?react'
import SharedStepIcon from '@Assets/icons/shared-step/icon.svg?react'
import { PATHS } from '@Common/consts';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { projectQueries } from '@Entities/project/queries';
import { ViewProjectStreams } from '@Features/stream/view-project-streams';
import { useQuery } from '@tanstack/react-query';
import { Button, Flex, type MenuProps, Skeleton, Typography } from 'antd';
import { ReactElement, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, useParams } from 'react-router-dom';
import { SideBarView } from './SideBarView.tsx';
import './style.css'

type MenuItem = Required<MenuProps>['items'][number];

interface IProps {
    nameSlot?: ReactNode
}

const SideBar = ({ nameSlot }: IProps): ReactElement => {
    const { t } = useTranslation();
    const logout = useAuthStore.use.logout()
    const { id } = useParams()
    const { data, isLoading } = useQuery({ ...projectQueries.byId(id!), enabled: !nameSlot && !!id })

    function getItem (
        label: ReactNode,
        key: string,
        icon?: ReactNode
    ): MenuItem {
        return {
            key,
            label: <NavLink to={ key }>{t(`menu.side.${label}`)}</NavLink>,
            icon
        } as MenuItem;
    }

    const items: MenuItem[] = [
        getItem('repository', PATHS.REPOSITORY.INDEX, <FolderOpenOutlined/>),
        getItem('runs', PATHS.RUNS.INDEX, <PlayCircleOutlined/>),
        getItem('records', PATHS.RECORDS.INDEX, <VideoCameraOutlined/>),
        // getItem('plans', PATHS.PLANS.INDEX, <ProfileOutlined/>),
        getItem('environments', PATHS.ENVIRONMENTS.INDEX, <AppstoreAddOutlined/>),
        getItem('variables', PATHS.VARIABLES.INDEX, <BracketsIcon/>),
        getItem('sharedSteps', PATHS.SHARED_STEPS.INDEX, <SharedStepIcon style={ { width: 16, height: 16 } }/>),
    ]

    const handleLogout = (): void => {
        logout()
    }

    return (
        <SideBarView
            bottom={
                <Button onClick={ handleLogout }>
                    {t('menu.side.sign_out')}
                </Button>
            }
            items={ items }
            top={ isLoading ? <Skeleton.Input style={ { height: '16.5px' } }/> : (
                <Flex style={ { width: '100%', paddingLeft: 12 } } vertical>
                    {nameSlot ?? <Typography.Text
                        style={ {
                            fontWeight: 700,
                            display: 'block',
                        } }
                    >
                        {data?.name}
                    </Typography.Text>}
                    <ViewProjectStreams/>
                </Flex>
            ) }
        />

    )
}

export { SideBarView, SideBar }

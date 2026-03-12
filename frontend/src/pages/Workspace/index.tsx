import { BILLING_ROLES, LOGS_ROLES, PATHS } from '@Common/consts';
import { PORTAL_ID } from '@Common/consts/portal.ts';
import { useThemeToken } from '@Common/hooks';
import { Portal } from '@Components/Portal';
import { EUserRole } from '@Entities/users/models';
import { WorkspaceSidebar } from '@Entities/workspace/components/Sidebar';
import { useWorkspaceStore } from '@Entities/workspace/store';
import { ShowTariffInfo } from '@Features/billing/sidebar-tariff-info';
import { ViewWorkspaceStreams } from '@Features/stream/view-workspace-streams';
import { EditWorkspaceName } from '@Features/workspace/edit-name';
import { useWorkspace } from '@Features/workspace/use-workspace';
import { ApiKeysPage } from '@Pages/Workspace/entities/ApiKeys';
import { BillingPage } from '@Pages/Workspace/entities/Billing';
import { LogsPage } from '@Pages/Workspace/entities/Logs';
import { UsersPage } from '@Pages/Workspace/entities/Users';
import { Layout } from 'antd';
import Sider from 'antd/es/layout/Sider';
import includes from 'lodash/includes';
import { Navigate, Route, Routes } from 'react-router-dom';
import { SHOW_ELEMENTS } from '../../common/consts/elements';

const WorkspacePage = () => {
    const token = useThemeToken()

    const workspace = useWorkspaceStore((state) => state.workspace)

    const { isLoading } = useWorkspace()

    return (
        <Layout hasSider={ true } style={ { height: '100%', background: token.colorBgBase } }>
            <Portal containerQuerySelector={ `#${PORTAL_ID.HEADER_EXTRA}` }>
                <ViewWorkspaceStreams/>
            </Portal>

            <Sider
                style={ {
                    height: '100%',
                    backgroundColor: `${token.colorFillQuaternary}`,
                    padding: `${token.paddingContentVerticalLG}px ${token.paddingContentHorizontal}px`
                } }
                theme="light"
                width={ 256 }
            >
                <WorkspaceSidebar
                    editSlot={ <EditWorkspaceName/> }
                    loading={ isLoading }
                    tariffSlot={ SHOW_ELEMENTS.BILLING.WORKSPACE_PAGE && (
                        workspace?.role === EUserRole.ADMIN && <ShowTariffInfo/>
                    ) }
                />
            </Sider>

            <Layout style={ { background: token.colorBgBase, overflow: 'auto' } }>
                <Routes>
                    <Route element={ <UsersPage/> } path={ PATHS.WORKSPACE.USERS.ABSOLUTE }/>
                    <Route element={ <ApiKeysPage/> } path={ PATHS.WORKSPACE.API_KEYS.ABSOLUTE }/>
                    {includes(LOGS_ROLES, workspace?.role) &&
                        <Route element={ <LogsPage/> } path={ PATHS.WORKSPACE.LOGS.ABSOLUTE }/>}
                    {includes(BILLING_ROLES, workspace?.role) && SHOW_ELEMENTS.BILLING.WORKSPACE_PAGE &&
                        <Route element={ <BillingPage/> } path={ PATHS.WORKSPACE.BILLING.ABSOLUTE }/>
                    }
                    <Route element={ <Navigate to="users"/> } index/>
                </Routes>
            </Layout>
        </Layout>
    )
}

export default WorkspacePage;

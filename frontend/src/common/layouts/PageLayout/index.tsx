import { SHOW_ELEMENTS } from '@Common/consts/elements';
import { useThemeToken } from '@Common/hooks';
import { PageHeader } from '@Common/layouts';
import { AvatarDropdown } from '@Features/workspace/avatar-dropdown';
import { ExpiredModal } from '@Features/workspace/expired-modal';
import { Layout } from 'antd';
import { Content } from 'antd/es/layout/layout';
import { ReactElement } from 'react';
import { Outlet } from 'react-router-dom';

export const PageLayout = (): ReactElement | null => {
    const token = useThemeToken()

    return (
        <Layout
            hasSider={ false }
            style={ { background: token.colorBgBase, minHeight: '100vh', overflow: 'hidden', height: '100vh' } }
        >
            <PageHeader renderAvatar={ <AvatarDropdown/> }/>

            <Content>
                { SHOW_ELEMENTS.BILLING.EXPIRED_MODAL && <ExpiredModal/>}
                <Outlet/>
            </Content>

        </Layout>
    )
}


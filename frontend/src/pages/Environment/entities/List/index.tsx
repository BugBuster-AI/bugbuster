import { BaseLayout } from '@Common/components';
import { LayoutTitle } from '@Components/LayoutTitle';
import { Toolbar } from '@Components/Toolbar';
import { EnvironmentsList } from '@Features/environments';
import { Flex } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

export const EnvironmentListPage = (): ReactElement => {

    const { t } = useTranslation()
    const navigate = useNavigate()

    return <Flex vertical>
        <LayoutTitle title={ t('environment_page.title') }/>

        <Toolbar
            addButton={ {
                title: t('environment_page.create'),
                props: {
                    onClick: () => navigate('create')
                }
            } }
            search={ null }/>

        <BaseLayout>
            <EnvironmentsList/>
        </BaseLayout>
    </Flex>
}



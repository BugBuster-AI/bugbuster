import { BaseLayout } from '@Common/components';
import { LayoutTitle } from '@Components/LayoutTitle';
import { Toolbar } from '@Components/Toolbar';
import { SharedStepsList } from '@Features/shared-steps';
import { Flex } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

export const SharedStepsListPage = () => {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const [query, setQuery] = useState('')

    return (
        <Flex vertical>
            <LayoutTitle title={ t('sharedStepsPage.title') }/>
            <Toolbar
                addButton={ {
                    title: t('sharedStepsPage.create'),
                    props: {
                        onClick: () => navigate('create')
                    }
                } }
                onSearch={ setQuery }
            />

            <BaseLayout>
                <SharedStepsList search={ query }/>
            </BaseLayout>
        </Flex>
    )
}

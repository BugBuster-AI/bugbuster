import { BaseLayout } from '@Common/components';
import { LayoutTitle } from '@Components/LayoutTitle';
import { Toolbar } from '@Components/Toolbar';
import { CreateVariableKit, VariableKitTable } from '@Pages/Variables/entities/List/components';
import { Flex } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

export const VariablesListPage = () => {
    const { t } = useTranslation()
    const [query, setQuery] = useState('')

    return (
        <Flex vertical>
            <LayoutTitle title={ t('variablesPage.title') }/>
            <Toolbar onSearch={ setQuery } renderButtons={ <CreateVariableKit/> }/>

            <BaseLayout>
                <VariableKitTable search={ query }/>
            </BaseLayout>
        </Flex>
    )
}

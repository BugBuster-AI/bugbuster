import { LayoutTitle } from '@Components/LayoutTitle';
import { Toolbar } from '@Components/Toolbar';
import { useProjectStore } from '@Entities/project/store';
import { useSuiteStore } from '@Entities/suite/store';
import { SuitesControl } from '@Features/suite';
import { CreateSuite } from '@Features/suite/create-suite';
import { Layout, Typography } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

export const SuitesPage = (): ReactElement => {
    const setSearchValue = useSuiteStore((state) => state.setSearchValue)
    const project = useProjectStore((state) => state.currentProject)
    const { t } = useTranslation()

    const handleSearch = (value: string) => {
        if (Boolean(value)) {
            setSearchValue(value)
        } else {
            setSearchValue(undefined)
        }
    }

    const title = `
        ${project?.case_count} ${t('repository_page.header.cases')} | ${project?.suite_count} 
        ${t('repository_page.header.suites')}`

    return (
        <Layout>
            {
                <LayoutTitle
                    info={
                        Boolean(project) && <Typography.Text type={ 'secondary' }>
                            {title}
                        </Typography.Text>
                    }
                    title={ 'Repository' }
                />
            }


            <Toolbar
                onSearch={ handleSearch }
                renderButtons={ <CreateSuite/> }
            />

            <SuitesControl/>
        </Layout>
    );
}

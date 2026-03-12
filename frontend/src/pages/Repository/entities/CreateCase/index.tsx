import { BaseLayout } from '@Common/components';
import { LayoutTitle } from '@Components/LayoutTitle';
import { CreateForm } from '@Features/test-case';
import { Flex, } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';


export const CreateCasePage = (): ReactElement => {
    const { t } = useTranslation();

    const title = t('create_test_case.go_to_back')

    return (
        <Flex style={ { width: '100%', height: '100%', maxWidth: 720 } } vertical>
            <LayoutTitle title={ title } withBack />

            <BaseLayout style={ { height: '100%', paddingBottom: 0 } }>
                <CreateForm />
            </BaseLayout>
        </Flex>
    )
}


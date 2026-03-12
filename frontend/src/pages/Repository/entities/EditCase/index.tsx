import { BaseLayout } from '@Common/components';
import { PATHS } from '@Common/consts';
import { useBackPath } from '@Common/utils/getBackPath.ts';
import { LayoutTitle } from '@Components/LayoutTitle';
import { ITestCase } from '@Entities/test-case/models';
import { EditForm } from '@Features/test-case/edit-case';
import { Flex, } from 'antd';
import { ReactElement, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';


export const EditCasePage = (): ReactElement => {
    const [data, setData] = useState<ITestCase | null>(null)
    const { t } = useTranslation();
    const { id } = useParams()
    const { getBackPath } = useBackPath()

    const backPath = () => {

        const path = PATHS.REPOSITORY.ABSOLUTE(id!)

        return getBackPath({
            root: path,
            rules: () => {
                if (data?.suite_id) {
                    return `${path}?suiteId=${data?.suite_id}`
                }

                return path
            }
        })
    }

    const title = t('edit_test_case.title')

    return (
        <Flex style={ { width: '100%', height: '100%', maxWidth: 720 } } vertical>
            <LayoutTitle backPath={ String(backPath()) } title={ title } withBack/>

            <BaseLayout style={ { height: '100%', paddingBottom: 0 } }>
                <EditForm onDataReady={ (data) => setData(data) }/>
            </BaseLayout>
        </Flex>
    )
}


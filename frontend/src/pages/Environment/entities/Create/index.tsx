import { BaseLayout } from '@Common/components';
import { PATHS } from '@Common/consts';
import { LayoutTitle } from '@Components/LayoutTitle';
import { CreateEnvironment } from '@Features/environments/create';
import { Flex } from 'antd';
import { ReactElement } from 'react';
import { useParams } from 'react-router-dom';

export const EnvironmentCreatePage = (): ReactElement => {
    const { id } = useParams()

    return <Flex style={ { height: '100%' } } vertical>
        <LayoutTitle
            backPath={ id ? PATHS.ENVIRONMENTS.ABSOLUTE(id) : undefined }
            title={ 'Create environment' }
            withBack
        />

        <BaseLayout style={ { flex: 1, width: 720 } }>
            <CreateEnvironment />
        </BaseLayout>
    </Flex>
}

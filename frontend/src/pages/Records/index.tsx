import { BaseLayout } from '@Common/components';
import { LayoutTitle } from '@Components/LayoutTitle';
import { Toolbar } from '@Components/Toolbar';
import { RecordsList } from '@Features/records/list';
import { Flex } from 'antd';

const RecordsPage = () => {

    return <Flex vertical>
        <LayoutTitle title={ 'Records' } />

        <Toolbar addButton={ null } />

        <BaseLayout>
            <RecordsList />
        </BaseLayout>
    </Flex>
}

export default RecordsPage

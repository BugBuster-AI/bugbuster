import { BaseLayout } from '@Common/components';
import { LayoutTitle } from '@Components/LayoutTitle';
import { Toolbar } from '@Components/Toolbar';
import { CreateRunFromCases } from '@Features/runs/create-run-from-cases';
import { RunsList } from '@Features/runs/list';
import { Flex } from 'antd';
import { ReactElement, useState } from 'react';

export const RunsListPage = (): ReactElement => {
    const [search, setSearch] = useState('')

    return (
        <Flex vertical>

            <LayoutTitle title="Runs" />

            <Toolbar
                onSearch={ setSearch }
                renderButtons={ <CreateRunFromCases /> }
            />

            <BaseLayout>
                <RunsList search={ search } />
            </BaseLayout>
        </Flex>
    )
}


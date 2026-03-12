import { CasesList } from '@Features/runs/create-run-from-cases/components/SelectCaseForm/components/Cases';
import { TopToolbar } from '@Features/runs/create-run-from-cases/components/SelectCaseForm/components/TopToolbar';
import {
    SuiteSelectableTree
} from '@Features/runs/create-run-from-cases/components/SelectCaseForm/components/Tree';
import { useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { Flex } from 'antd';

export const SelectCaseForm = () => {
    const executionMode = useCreateRunStore((state) => state.currentExecutionMode)

    /*
     * Note: We removed the internal state and the tabs. 
     * The execution mode is now driven globally by the CreateRunStore.
     */

    return (
        <Flex style={ { height: '75vh' } } vertical>
            <TopToolbar executionMode={ executionMode } />
            <Flex gap={ 24 } style={ { height: '100%', paddingBlock: '16px' } }>
                <SuiteSelectableTree executionMode={ executionMode } />

                <CasesList executionMode={ executionMode } />
            </Flex>
        </Flex>
    )
}

export { SuiteSelectableTree } from './components'


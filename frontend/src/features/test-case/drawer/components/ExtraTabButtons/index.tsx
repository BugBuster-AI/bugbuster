import { useTestCaseStore } from '@Entities/test-case';
import { ETestCaseType } from '@Entities/test-case/models';
import { CopyButton, DeleteButton, EditCaseButton, RunButton } from '@Features/test-case/buttons';
import { Flex } from 'antd';
import head from 'lodash/head';
import { ReactElement } from 'react';

export const ExtraTabButtons = ({ caseId, onClose }: { caseId: string, onClose: () => void }): ReactElement => {
    const currentCase = useTestCaseStore((state) => state.currentCase)
    const setCurrentCase = useTestCaseStore((state) => state.setCurrentCase)

    return (
        <Flex align={ 'center' } gap={ 16 }>

            <Flex gap={ 8 }>
                <EditCaseButton case_id={ caseId } thisTab/>
                <CopyButton case_id={ [caseId] } onSuccess={ (data) => setCurrentCase(head(data)) }/>
                <DeleteButton
                    case_id={ [caseId] }
                    onClick={ onClose }
                />
            </Flex>

            <RunButton case_id={ caseId } disabled={ currentCase?.type === ETestCaseType.manual }/>
        </Flex>
    )
}

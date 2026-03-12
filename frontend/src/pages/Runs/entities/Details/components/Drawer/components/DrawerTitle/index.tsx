import { EStatusIndicator, StatusIndicator } from '@Common/components';
import { ERunStatus, ITestCaseInGroupedRun } from '@Entities/runs/models';
import { useTestCaseStore } from '@Entities/test-case';
import { TestTypeIcon } from '@Entities/test-case/components/Icons';
import { Flex, Typography } from 'antd';

const getStatus = (status: ERunStatus): EStatusIndicator => {
    switch (status) {
        case ERunStatus.PASSED:
            return EStatusIndicator.SUCCESS
        case ERunStatus.FAILED:
            return EStatusIndicator.ERROR
        case ERunStatus.IN_PROGRESS:
            return EStatusIndicator.LOADING
        case ERunStatus.IN_QUEUE:
            return EStatusIndicator.LOADING
        case ERunStatus.AFTER_STEP_FAILURE:
            return EStatusIndicator.WARNING
        default:
            return EStatusIndicator.IDLE
    }
}

export const DrawerTitle = () => {
    const testCase = useTestCaseStore((state) => state.currentCase)

    const testCaseGrouped = testCase as ITestCaseInGroupedRun

    if (!testCase) return null

    return (
        <Flex gap={ 8 }>
            <StatusIndicator
                status={ getStatus(testCaseGrouped?.actual_status) }
            />
            <Flex gap={ 4 }>
                <TestTypeIcon type={ testCase.type }/>
                <Typography.Text

                    ellipsis={ true }
                    style={ {
                        maxWidth: '600px',
                        width: '100%'
                    } }>
                    {testCase.name}
                </Typography.Text>
            </Flex>
        </Flex>
    )
}

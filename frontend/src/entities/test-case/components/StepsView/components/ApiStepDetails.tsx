import { StatusLabel } from '@Components/StatusLabel';
import { ILocalStepData } from '@Entities/test-case/models';
import { Flex } from 'antd';
import map from 'lodash/map';
import size from 'lodash/size';

interface IProps {
    step: ILocalStepData
}

export const ApiStepDetails = ({ step }: IProps) => {

    const extra = step.extra

    if (size(extra?.validations_log) <= 0) {
        return null
    }

    return (
        <Flex>
            {map(extra?.validations_log, (item, index) => {
                return <StatusLabel key={ `validation_log_${index}` } title={ item } checkStatusInTitle/>
            })}
        </Flex>
    )

}

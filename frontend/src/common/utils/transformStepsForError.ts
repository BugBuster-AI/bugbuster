import { IStep } from '@Common/types/steps';
import { STEP_GROUPS_TO_MAP } from '@Common/utils/test-case';
import { EStepGroup } from '@Entities/runs/models';
import forEach from 'lodash/forEach';
import get from 'lodash/get';
import map from 'lodash/map';

interface IProps {
    steps?: IStep[];
    before_steps?: IStep[];
    after_steps?: IStep[];
    before_browser_start?: IStep[]
}


export const transformStepsForError = (data: IProps) => {
    let localIndex = 0

    const steps = {} as Record<EStepGroup, IStep[]>
    const stepsArray: IStep[] = []

    forEach(STEP_GROUPS_TO_MAP, (stepKey) => {
        steps[stepKey] = map((get(data, stepKey, [])), (step) => {
            const stepWithIndex = { ...step, stepGroup: stepKey, localIndex: localIndex }

            stepsArray.push(stepWithIndex)

            localIndex++


            return stepWithIndex
        })
    })


    return stepsArray
};

import { IRunStep, TStepGroup } from '@Entities/runs/models';
import { ILocalRunData, ILocalStepData } from '@Entities/test-case/models';
import groupBy from 'lodash/groupBy';
import orderBy from 'lodash/orderBy';
import reduce from 'lodash/reduce';

type TGroupedSteps = Record<TStepGroup, IRunStep[]>

// legacy func
export const groupSteps = (steps: IRunStep[]): TGroupedSteps => {

    const groupedSteps = groupBy(steps, 'step_group');

    const order: TStepGroup[] = ['before_browser', 'before', 'step', 'after'];

    const sortedKeys = orderBy(order, (key) => order.indexOf(key));

    return reduce(sortedKeys, (acc, value) => {
        acc[value] = groupedSteps[value] || [];

        return acc;
    }, {} as TGroupedSteps);
}

export const groupLocalSteps = (steps: ILocalStepData[]): ILocalRunData['steps'] => {
    const groupedSteps = groupBy(steps, 'group');

    // HINT: !важен порядок
    const order: TStepGroup[] = ['before_browser', 'before', 'step', 'after'];

    const sortedKeys = orderBy(order, (key) => order.indexOf(key));

    return reduce(sortedKeys, (acc, value) => {
        acc[value] = groupedSteps[value] || [];

        return acc;
    }, {} as ILocalRunData['steps']);
}

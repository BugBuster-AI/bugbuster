import { IStep } from '@Common/types';
import { GROUP_STEPS_ORDER } from '@Common/utils/test-case/consts.ts';
import groupBy from 'lodash/groupBy';
import orderBy from 'lodash/orderBy';
import reduce from 'lodash/reduce';

export const groupStepsArray = <T = IStep>(
    steps: IStep[],
    order = GROUP_STEPS_ORDER,
    transform?: (val: IStep) => T) => {
    const groupedSteps = groupBy(steps, 'stepGroup')
    const sortedKeys = orderBy(order, (key) => order.indexOf(key));

    return reduce(sortedKeys, (acc, value) => {
        const rawValue = groupedSteps[value] || [];

        //@ts-ignore
        acc[value] = transform ? rawValue.map(transform) : rawValue;

        return acc;
    }, {} as Record<(typeof order)[number], T[]>);
}


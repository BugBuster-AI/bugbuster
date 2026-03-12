import { IStep } from '@Common/types/steps';
import { httpStepToLocal } from '@Common/utils/test-case';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ITestCase } from '@Entities/test-case/models';
import entries from 'lodash/entries';
import forEach from 'lodash/forEach';
import get from 'lodash/get';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';

type TStepsPayload = Pick<ITestCase, 'steps' | 'before_steps' | 'after_steps' | 'before_browser_start'>

export interface IReturnData {
    steps: IStep[];
    before_steps: IStep[];
    after_steps: IStep[];
    before_browser_start: IStep[]
}

interface IProps {
    steps: TStepsPayload;
    results: Record<string | number, string>[];
    reasons?: Record<number | string, string>
    stepsData?: unknown[]
}

export const getTransformedSteps = ({ steps, results, reasons = {}, stepsData }: IProps): IReturnData => {
    let commonIndex = 0

    const baseSections = {
        before_browser_start: map(steps?.before_browser_start, (step) => {
            const index = commonIndex

            commonIndex += 1

            return httpStepToLocal(step, index, get(stepsData, index, null))
        }) || [],
        before_steps: steps?.before_steps?.map((step) => {
            const index = commonIndex

            commonIndex += 1

            return httpStepToLocal(step, index, get(stepsData, index, null))
        }) || [],
        steps: steps?.steps?.map((step) => {

            const index = commonIndex

            commonIndex += 1

            return httpStepToLocal(step, index, get(stepsData, index, null))
        }) || [],
        after_steps: steps?.after_steps?.map((step) => {
            const index = commonIndex

            commonIndex += 1

            return httpStepToLocal(step, index, get(stepsData, index, null))
        }) || []
    };

    // Создаем плоский список результатов с валидными индексами
    const entriesResults = (results || []).flatMap((result) =>
        map(entries(result), ([key, value]) => ({
            index: parseInt(key, 10),
            result: value
        })
        ).filter((entry) => !isNaN(entry.index)))

    // Определяем границы секций
    const sectionBoundaries = {
        beforeBrowser: baseSections.before_browser_start.length,
        before: baseSections.before_steps.length,
        main: baseSections.steps.length,
        after: baseSections.after_steps.length
    };


    // Функция для обработки секции
    const processSection = (section: IStep[], startIdx: number, endIdx: number) => {
        const sectionResults = entriesResults
            .filter(({ index }) => index >= startIdx && index < endIdx)
            .sort((a, b) => a.index - b.index); // Сортировка по возрастанию для правильного порядка вставки

        const processed = [...section];


        let j = 0

        for (const { index, result } of sectionResults) {
            const localIndex = index - startIdx + j;

            j += 1
            processed.splice(localIndex + 1, 0, {
                step: result,
                type: EStepType.RESULT,
                indexFor: index
            });

        }

        return processed;
    }

    const beforeBrowserStartProcessed = processSection(
        baseSections.before_browser_start,
        0,
        sectionBoundaries.beforeBrowser
    )

    const beforeStepsProcessed = processSection(
        baseSections.before_steps,
        sectionBoundaries.beforeBrowser,
        sectionBoundaries.before + sectionBoundaries.beforeBrowser
    )

    const mainStepsProcessed = processSection(
        baseSections.steps,
        sectionBoundaries.before + sectionBoundaries.beforeBrowser,
        sectionBoundaries.before + sectionBoundaries.main + sectionBoundaries.beforeBrowser
    )

    const afterStepsProcessed = processSection(
        baseSections.after_steps,
        sectionBoundaries.before + sectionBoundaries.main + sectionBoundaries.beforeBrowser,
        sectionBoundaries.before + sectionBoundaries.main + sectionBoundaries.after + sectionBoundaries.beforeBrowser
    )

    // Объединяем все секции
    const allSteps = [
        ...beforeBrowserStartProcessed,
        ...beforeStepsProcessed,
        ...mainStepsProcessed,
        ...afterStepsProcessed
    ];

    if (!isEmpty(reasons)) {
        forEach(allSteps, (item, index) => {
            item.extraInfo = get(reasons, index, undefined)
        })
    }

    return {
        before_browser_start: beforeBrowserStartProcessed,
        before_steps: beforeStepsProcessed,
        steps: mainStepsProcessed,
        after_steps: afterStepsProcessed
    };
};


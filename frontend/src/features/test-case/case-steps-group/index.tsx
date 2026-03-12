import { editStepGroups, httpStepToLocal } from '@Common/utils/test-case';
import { useProjectStore } from '@Entities/project/store';
import { EStepGroup } from '@Entities/runs/models';
import { sharedStepsQueries } from '@Entities/shared-steps';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { StepGroup } from '@Entities/test-case/components/StepGroup';
import { ITestCase } from '@Entities/test-case/models';
import { useQuery } from '@tanstack/react-query';
import entries from 'lodash/entries';
import map from 'lodash/map';
import reduce from 'lodash/reduce';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    testCase?: ITestCase
}

export const StepsCaseGroup = ({ testCase }: IProps) => {
    const { t } = useTranslation()
    const { currentProject } = useProjectStore()
    const { data } = useQuery(sharedStepsQueries.list({ project_id: currentProject?.project_id! }))
    const entriesData = useMemo(() => reduce(data, (acc, item) => {
        acc[item.shared_steps_id] = item.name

        return acc
    }, {}), [data])
    const preparedSteps = useMemo(() =>
        editStepGroups(
            testCase,
            (step, stepKey, index) => {
                const localStep = httpStepToLocal(step, index, undefined, stepKey as EStepGroup)

                if (localStep.type === EStepType.SHARED_STEP) {
                    const value = entriesData[localStep.step]

                    return {
                        ...localStep,
                        step: value
                    }
                }

                return localStep
            }
        ),
    [testCase, data])


    return map(entries(preparedSteps), ([key, value], index) => {
        return <StepGroup key={ `step-group-${index}` } name={ t(`stepGroups.${key}`) } steps={ value }/>
    })

}

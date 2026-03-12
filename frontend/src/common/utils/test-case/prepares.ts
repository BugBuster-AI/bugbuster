import { toUnicode } from 'punycode';
import { IStep } from '@Common/types';
import { insertIndexesInArray } from '@Common/utils/test-case/insert-indexes.ts';
import { httpStepToLocal, localStepToHttp } from '@Common/utils/test-case/steps.tsx';
import { EStepGroup } from '@Entities/runs/models';
import { EStepType, IBaseForm } from '@Entities/test-case/components/Form/models.ts';
import { ITestCase, ITestCaseStep } from '@Entities/test-case/models';
import forEach from 'lodash/forEach';
import get from 'lodash/get';
import map from 'lodash/map';

const decodePunycodeUrl = (url: string) => {
    if (!url || typeof url !== 'string' || !url.includes('xn--')) {
        return url
    }

    try {
        const parsed = new URL(url)
        const decodedHost = toUnicode(parsed.hostname)

        if (decodedHost === parsed.hostname) {
            return url
        }

        const auth = parsed.username || parsed.password
            ? `${parsed.username}${parsed.password ? `:${parsed.password}` : ''}@`
            : ''
        const port = parsed.port ? `:${parsed.port}` : ''

        return `${parsed.protocol}//${auth}${decodedHost}${port}${parsed.pathname}${parsed.search}${parsed.hash}`
    } catch {
        return url
    }
}

export const STEP_GROUPS_TO_MAP = [
    EStepGroup.BEFORE_BROWSER,
    EStepGroup.BEFORE,
    EStepGroup.STEPS,
    EStepGroup.AFTER,
]

export const editStepGroups =
    <T>(
        data?: ITestCase,
        cb?: (step: ITestCaseStep, stepKey: string, index: number) => T,
        groupsArray: string[] = STEP_GROUPS_TO_MAP
    ) => {
        const localSteps = {} as Record<EStepGroup, T[]>

        forEach(groupsArray, (stepKey) => {
            if (cb) {
                localSteps[stepKey] = map(get(data, stepKey, []), (step, index) => cb(step, stepKey, index))

                return
            }
            localSteps[stepKey] = get(data, stepKey, [])
        })

        return localSteps
    }

export const mapHttpToLocal = (steps: ITestCaseStep[], group: EStepGroup) => {

    return map(steps, (item, index) => httpStepToLocal(item, index, null, group))
}

const mapToIndexStep = (steps: Record<string | number, string>[], type?: EStepType) => {
    return map(steps, (item) => {
        const key = Number(Object.keys(item)[0])

        return {
            [key]: {
                step: item[key],
                type,
            } as IStep,
        }
    })
}

export const insertIndexesInSteps = (data?: ITestCase, transform?: (step: IStep) => IStep) => {
    const initialStepsArray = [
        ...mapHttpToLocal(get(data, 'before_browser_start', []), EStepGroup.BEFORE_BROWSER),
        ...mapHttpToLocal(get(data, 'before_steps', []), EStepGroup.BEFORE),
        ...mapHttpToLocal(get(data, 'steps', []), EStepGroup.STEPS),
        ...mapHttpToLocal(get(data, 'after_steps', []), EStepGroup.AFTER),
    ]

    const indexLayers = [
        mapToIndexStep(get(data, 'validation_steps', []), EStepType.RESULT),
    ]

    return insertIndexesInArray({
        indexLayers,
        items: initialStepsArray,
        transform,
        transformIndexItem: (item) => {
            let group: EStepGroup | null

            group = item?.stepGroup ?? get(item, 'originalValue', null)?.stepGroup ?? null

            if (item.type === EStepType.SHARED_STEP && Number(item?.originalIndex) < 0) {
                group = EStepGroup.BEFORE
            }
            // HINT: Костыль
            if (item?.type === EStepType.RESULT) {
                group = EStepGroup.STEPS
            }

            return {
                ...item,
                stepGroup: group,
            } as IStep
        }
    })
}

// Подготовка степов для редактирования кейса
export const prepareForEdit = (data?: ITestCase) => {
    if (!data) {
        return null
    }

    const localData = { ...data }

    localData.url = decodePunycodeUrl(localData.url)
    const localSteps = {} as Record<EStepGroup, IStep[]>

    forEach(STEP_GROUPS_TO_MAP, (stepKey) => {
        localSteps[stepKey] = mapHttpToLocal(get(localData, stepKey, []), stepKey)
    })

    return {
        ...localData,
        ...localSteps
    }
}

// Подготовка степов при сохранении кейса
export const prepareForSubmit = <T extends IBaseForm>(data: T) => {
    const updatedData = { ...data } as unknown as ITestCase
    const httpSteps = {} as Record<EStepGroup, ITestCaseStep[]>

    forEach(STEP_GROUPS_TO_MAP, (stepKey) => {
        httpSteps[stepKey] = map((get(data, stepKey, [])), localStepToHttp)
    })

    if (!data?.environment_id) {
        updatedData.environment_id = null
    }

    return {
        ...updatedData,
        ...httpSteps,
    }
}

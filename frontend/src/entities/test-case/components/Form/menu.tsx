import { CopyOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { IStep, TranslationType } from '@Common/types';
import { EStepGroup } from '@Entities/runs/models';
import { EMenuActions, EMenuExpectedResultActions, EStepType } from '@Entities/test-case/components/Form/models.ts';
import { Flex, FormInstance, Radio, Typography } from 'antd';
import { ItemType } from 'antd/es/menu/interface';
import compact from 'lodash/compact';
import includes from 'lodash/includes';
import map from 'lodash/map';
import size from 'lodash/size';
import { useTranslation } from 'react-i18next';

interface IFuncProps {
    add: (...args: any) => void
    remove: (index: number) => void
    groupType: EStepGroup
    actionType: EMenuActions | EMenuExpectedResultActions
    form: FormInstance,
    indexNumber: number
    restProps?: Record<string, any>
    updateStep: (value: Partial<IStep>) => void
}

interface IGetMenuProps {
    stepTypes?: EStepType[]
    stepData?: IStep
}

const MENU_ITEM = (t: TranslationType) => ({
    [EMenuActions.ADD_API]: {
        key: EMenuActions.ADD_API,
        label: t('create_test_case.menu.add_api'),
        icon: <PlusOutlined style={ { color: 'black', fontSize: 16 } }/>
    },
    [EMenuActions.ADD_STEP]: {
        key: EMenuActions.ADD_STEP,
        label: t('create_test_case.menu.add_step'),
        icon: <PlusOutlined style={ { color: 'black', fontSize: 16 } }/>
    },
    [EMenuActions.ADD_RESULT]: {
        key: EMenuActions.ADD_RESULT,
        icon: <PlusOutlined style={ { color: 'black', fontSize: 16 } }/>,
        label: t('create_test_case.menu.add_result'),
    },
    [EMenuActions.DELETE_STEP]: {
        key: EMenuActions.DELETE_STEP,
        label: t('create_test_case.menu.delete_step'),
        style: { color: 'red', width: 220 },
        icon: <DeleteOutlined style={ { color: 'red', fontSize: 16 } }/>
    },
    [EMenuActions.CLONE_STEP]: {
        key: EMenuActions.CLONE_STEP,
        label: t('create_test_case.menu.clone_step'),
        icon: <CopyOutlined style={ { color: 'black', fontSize: 16 } }/>
    },
    [EMenuActions.ADD_SHARED_STEP]: {
        key: EMenuActions.ADD_SHARED_STEP,
        icon: <PlusOutlined style={ { color: 'black', fontSize: 16 } }/>,
        label: t('create_test_case.menu.add_shared_step'),
    }
})

const STEP_ACTIONS_BY_STEP_TYPE = {
    [EStepType.STEP]: [EStepType.STEP, EStepType.RESULT, EStepType.API, EStepType.SHARED_STEP],
    [EStepType.RESULT]: [EStepType.STEP, EStepType.RESULT, EStepType.API, EStepType.SHARED_STEP],
    [EStepType.API]: [EStepType.STEP, EStepType.RESULT, EStepType.API, EStepType.SHARED_STEP],
    [EStepType.SHARED_STEP]: [EStepType.STEP, EStepType.RESULT, EStepType.API, EStepType.SHARED_STEP]
}

function getLabelWithCheck (label: string, needCheck: boolean = false) {
    
    return (
        <Flex align="center" gap={ 16 } justify="space-between">
            <Typography>{label}</Typography> 
            <Radio checked={ needCheck } type="radio" />
        </Flex>
    )
}

export const useMenuFeatures = () => {
    const { t } = useTranslation()

    const STEP = MENU_ITEM(t)
    const STEP_ACTIONS_CONFIG = {
        [EStepType.STEP]: STEP[EMenuActions.ADD_STEP],
        [EStepType.RESULT]: STEP[EMenuActions.ADD_RESULT],
        [EStepType.API]: STEP[EMenuActions.ADD_API],
        [EStepType.SHARED_STEP]: STEP[EMenuActions.ADD_SHARED_STEP]
    }

    const handleFeatureClick = (
        { form, indexNumber, actionType, updateStep, groupType, remove, add, restProps }: IFuncProps
    ) => {
        const nextIndex = indexNumber + 1
        const stepGroup = groupType

        switch (actionType) {
            case EMenuActions.ADD_STEP:
                add({ type: EStepType.STEP, stepGroup, ...restProps }, nextIndex)
                break
            case EMenuActions.ADD_API:
                add({ type: EStepType.API, stepGroup, ...restProps }, nextIndex)
                break
            case EMenuActions.ADD_RESULT:
                add({ type: EStepType.RESULT, stepGroup, ...restProps }, nextIndex)
                break
            case EMenuActions.CLONE_STEP:
                const currentValues = form.getFieldValue([groupType, indexNumber])

                add({ ...currentValues, stepGroup, ...restProps }, nextIndex);
                break
            case EMenuActions.DELETE_STEP:
                remove(indexNumber)
                break
            case EMenuActions.ADD_SHARED_STEP:
                add({ type: EStepType.SHARED_STEP, stepGroup, ...restProps }, nextIndex)
                break
            case EMenuExpectedResultActions.SET_DYNAMIC_CHANGE_VERIF:
                updateStep({
                    extraData: {
                        use_single_screenshot: false
                    }
                })
                break;

            case EMenuExpectedResultActions.SET_STATE_VERIF:
                updateStep({
                    extraData: {
                        use_single_screenshot: true
                    }
                })
                break;
            default :
                break;
        }
    }

    const getMenu = ({ stepTypes, stepData }: IGetMenuProps) => {
        const currentStep = stepData?.type
        const STEP = MENU_ITEM(t)

        const COMMON_ITEMS = [
            { type: 'divider' },
            STEP[EMenuActions.CLONE_STEP],
            STEP[EMenuActions.DELETE_STEP],
        ]
        let FUNCTIONAL_STEPS: ItemType[] = []

        if (currentStep === EStepType.RESULT) {
        
            const useSingleScreenshot = stepData?.extraData?.use_single_screenshot

            FUNCTIONAL_STEPS = [
                {
                    type: 'group',
                    label: 'Verification Mode',
                    key: 'verification_state',
                    children: [
                        {
                            type: 'item',
                            label: getLabelWithCheck(t('resultVerifications.state'), 
                                useSingleScreenshot === true 
                                || useSingleScreenshot === undefined 
                                || useSingleScreenshot === null),
                            key: EMenuExpectedResultActions.SET_STATE_VERIF,
                        },
                        {
                            type: 'item',
                            label: getLabelWithCheck(t('resultVerifications.dynamic'), useSingleScreenshot === false),
                            key: EMenuExpectedResultActions.SET_DYNAMIC_CHANGE_VERIF,
                        }
                    ],
                }
            ]
        }

        if (size(FUNCTIONAL_STEPS)) {FUNCTIONAL_STEPS.unshift({ type: 'divider' })}

        const acceptedActions = STEP_ACTIONS_BY_STEP_TYPE?.[currentStep as EStepType]
        const resultItems = [
            ...compact(map(stepTypes, (feature) => {
                if (acceptedActions && !includes(acceptedActions, feature)) {
                    return null
                }

                return STEP_ACTIONS_CONFIG[feature]
            })),
            ...COMMON_ITEMS,
            ...FUNCTIONAL_STEPS
        ]

        return {
            items: resultItems as ItemType[],
        }
    }


    return { getMenu, featureClick: handleFeatureClick }
}

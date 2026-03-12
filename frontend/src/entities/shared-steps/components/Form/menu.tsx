import { CopyOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { TranslationType, TStepsVariants } from '@Common/types';
import { EMenuActions, EStepType } from '@Entities/test-case/components/Form/models.ts';
import { FormInstance } from 'antd';
import { useTranslation } from 'react-i18next';

interface IFuncProps {
    add: (...args: any) => void
    remove: (index: number) => void
    groupType: TStepsVariants
    actionType: EMenuActions
    form: FormInstance,
    indexNumber: number
}

interface IGetMenuProps extends Pick<IFuncProps, 'groupType'> {
    stepTypes?: EStepType[]
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
    }
})

export const useMenuFeatures = () => {
    const { t } = useTranslation()

    const handleFeatureClick = ({ form, indexNumber, actionType, groupType, remove, add }: IFuncProps) => {
        switch (actionType) {
            case EMenuActions.ADD_STEP:
                add({ type: EStepType.STEP }, indexNumber + 1)
                break
            case EMenuActions.ADD_API:
                add({ type: EStepType.API }, indexNumber + 1)
                break
            case EMenuActions.ADD_RESULT:
                add({ type: EStepType.RESULT }, indexNumber + 1)
                break
            case EMenuActions.CLONE_STEP:
                const currentValues = form.getFieldValue([groupType, indexNumber])

                add({ ...currentValues }, indexNumber + 1);
                break
            case EMenuActions.DELETE_STEP:
                remove(indexNumber)
                break
            default :
                break;
        }
    }

    const getMenu = ({ groupType }: IGetMenuProps) => {
        let resultItems

        const STEP = MENU_ITEM(t)

        const COMMON_STEPS = [
            { type: 'divider' },
            STEP[EMenuActions.CLONE_STEP],
            STEP[EMenuActions.DELETE_STEP],
        ]

        switch (groupType) {
            case 'steps':
                resultItems = [
                    STEP[EMenuActions.ADD_STEP],
                    STEP[EMenuActions.ADD_API],
                    ...COMMON_STEPS
                ]
                break
            default:
                resultItems = [
                    STEP[EMenuActions.ADD_STEP],
                    STEP[EMenuActions.ADD_API],
                    ...COMMON_STEPS
                ]
                break
        }

        return {
            items: resultItems,
        }
    }


    return { getMenu, featureClick: handleFeatureClick }
}

import { PlusOutlined } from '@ant-design/icons';
import { EStatusIndicator, StatusIndicator } from '@Common/components';
import { METHOD_COLORS } from '@Common/consts/common.ts';
import { CLASSNAMES } from '@Common/consts/css.ts';
import { useThemeToken } from '@Common/hooks';
import { formatVariableToComponent, replaceWithReactNode } from '@Common/utils/formatVariable.tsx';
import { IGetCoordinatesResponse } from '@Entities/common/models/get-coordinates.ts';
import { ERunStatus, IRunStep } from '@Entities/runs/models';
import { ContextScreenshotIcon } from '@Entities/test-case/components/ContextScreenshotIcon';
import { EStepType } from '@Entities/test-case/components/Form/models.ts';
import { IExtraCaseType } from '@Entities/test-case/models/test-case-variables.ts';
import { variableQueries } from '@Entities/variable/queries';
import { AutocompleteVariablesTextarea } from '@Features/variable';
import { EditModeActions } from '@Pages/RunningCase/components/SingleRunStepCard/components/EditModeActions.tsx';
import { ViewModeBottom } from '@Pages/RunningCase/components/SingleRunStepCard/components/ViewModeBottom.tsx';
import { NOT_EDITABLE_ACTION_TYPES } from '@Pages/RunningCase/components/SingleRunStepCard/consts.ts';
import { SingleRunStepContext } from '@Pages/RunningCase/components/SingleRunStepCard/context';
import stylesCSS from '@Pages/RunningCase/components/SingleRunStepCard/SingleRunStepCard.module.scss'
import { useRunningStore } from '@Pages/RunningCase/store';
import { useQuery } from '@tanstack/react-query';
import { Button, Dropdown, Flex, GlobalToken, Menu, Typography } from 'antd';
import cn from 'classnames';
import find from 'lodash/find';
import includes from 'lodash/includes';
import isEmpty from 'lodash/isEmpty';
import isObject from 'lodash/isObject';
import isString from 'lodash/isString';
import map from 'lodash/map';
import reduce from 'lodash/reduce';
import { ComponentProps, CSSProperties, isValidElement, ReactNode, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IEditStepReturn {
    name: string
}

export interface ISingleRunStepCardProps {
    // Уникальный id степа
    stepId: string
    // Объект степа из рана
    stepItem: IRunStep
    // Название степа
    title: string | ReactNode;
    // Не форматированное название
    originalTitle?: string
    // Описание степа
    description?: string | ReactNode
    // Время выполнения степа
    time?: string | false;
    // Статус степа
    status?: EStatusIndicator
    // Тип степа (api, action)
    stepType?: EStepType
    // Название действия
    actionName?: string | ReactNode;
    // Номер степа
    stepIndex?: string | number
    // Функция клика по карточке
    onClick?: () => void,
    // Доп информация о шаге
    stepInfo?: string | number
    // Экстра информация для степа
    extra?: IExtraCaseType

    // выделен ли степ
    isSelected?: boolean

    selectCase?: () => void
    style?: CSSProperties
    noStatus?: boolean
    disabled?: boolean;
    statusProps?: ComponentProps<typeof StatusIndicator>
    isLoading?: boolean,
    canInsertStepAfter?: boolean
    
    contextIcon?: boolean
    isEditing?: boolean
    editable?: boolean
    editActions?: {
        onChangeEdit?: (val: boolean) => void
        onSave?: (data: IEditStepReturn) => Promise<void>
        onCheck?: (data: IGetCoordinatesResponse) => Promise<void>
        onCancel?: () => void
    }
}

const getStyles = (token: GlobalToken) => {
    return {
        backgroundColor: token.colorFillAlter,
        padding: 16,
        width: '100%',
        borderRadius: token.sizeXS,
        border: `1px solid ${token.colorBorderSecondary}`,
        cursor: 'pointer'
    }
}

export const SingleRunStepCard = ({
    ...props
}: ISingleRunStepCardProps) => {
    const {
        stepItem,
        onClick,
        status = EStatusIndicator.IDLE,
        isEditing = false,
        stepIndex,
        actionName,
        isLoading,
        description,
        stepId,
        title,
        originalTitle,
        noStatus = false,
        statusProps,
        editActions,
        style: overrideStyle,
        canInsertStepAfter,
        stepType,
        disabled,
        editable: rawEditable = false,
        contextIcon
    } = props || {}
    const currentRun = useRunningStore((state) => state.currentRun)
    const setVariablesList = useRunningStore((state) => state.setVariablesList)
    const currentCase = currentRun?.case
    const setEditingStep = useRunningStore((state) => state.setEditingStep)
    const updateEditingStep = useRunningStore((state) => state.updateEditingStep)
    const currentEditingStep = find(
        useRunningStore((state) => state.editingSteps), 
        (item) => item.id === stepItem.localUUID
    )

    const currentError = currentEditingStep?.step?.error
    // Получаем переменные из кита текущего кейса для автокомплита
    const { data: variablesList } = useQuery(variableQueries.variableListByName({
        project_id: currentCase?.project_id!,
        variables_kit_name: currentCase?.variables!,
    }, { enabled: !!currentCase?.variables && !!currentCase?.project_id && isEditing }))

    const formattedVariablesList = map(variablesList?.variables_details, (item) => item.variable_name ?? '')

    const variableObject = useMemo(() => reduce(variablesList?.variables_details, (acc, value) => {
        acc[value.variable_name ?? ''] = value.computed_value

        return acc
    }, {}), [variablesList])

    useEffect(() => {
        if (variableObject) {
            setVariablesList(variableObject)
        }
    }, [variableObject]);

    const token = useThemeToken()
    const styles = getStyles(token)
    const [tempValue, setTempValue] = useState(originalTitle)
    const [tempGeneratedData, setTempGeneratedData] = useState<IGetCoordinatesResponse | undefined>(undefined)
    const [loading, setLoading] = useState<boolean>(false)
    
    const [useSingleScreenshot, setUseSingleScreenshot] = useState<boolean | undefined>(
        stepItem?.extra?.use_single_screenshot
    )

    const isNotEditableRules = isString(actionName) ? includes(NOT_EDITABLE_ACTION_TYPES, actionName) : false

    const isEditable =
        rawEditable &&
        !isNotEditableRules &&
        !disabled &&
        stepType !== EStepType.API &&
        !isEmpty(stepItem.before)

    const getActionNameStyles = (): CSSProperties => {
        switch (stepType) {
            case EStepType.API:
                return {
                    fontWeight: 'bold',
                    color: METHOD_COLORS?.
                        [isString(actionName) ? actionName.toUpperCase() : ''] as keyof typeof METHOD_COLORS
                        || token.colorTextDescription
                }
            default:
                return {
                    color: token.colorTextDescription
                }
        }
    }

    const handleChangeInput = (value: string) => {
        setTempValue(value)

        updateEditingStep(stepItem.localUUID!, {
            raw_step_description: value,
            extra: {
                ...stepItem.extra
            },
            original_step_description: value,
        })

        if (value) {
            /*
             * if (currentEditingStep?.step?.errorType === 'empty') {
             *     updateEditingStep(stepItem.localUUID!, {
             *         raw_step_description: value,
             *         error: undefined,
             *         errorType: undefined
             *     })
             * }
             */
            updateEditingStep(stepItem.localUUID!, {
                raw_step_description: value,
                error: undefined,
                errorType: undefined
            })
        } else {
            updateEditingStep(stepItem.localUUID!, {
                raw_step_description: value,
                error: 'Value is required',
                errorType: 'empty'
            })
        }
    }

    // Нажание на карточку
    const handleClick = () => {
        if (disabled) return

        onClick && onClick()
    }

    // Изменение режима редактирования
    const handleChangeEditing = (value: boolean) => {
        if (value) {
            setEditingStep({
                id: stepItem.localUUID!,
                step: stepItem
            })
        }

        if (editActions) {
            editActions?.onChangeEdit?.(value)
        }
    }

    const disabledStyles = disabled ? {
        opacity: 0.5,
        cursor: 'not-allowed'
    } : {}

    const formattedTitle = () => {
        if (isValidElement(title)) {
            return title
        }
        if (isObject(title)) {
            return JSON.stringify(title)
        }

        if (isString(title)) {

            return replaceWithReactNode(title,
                (variable, index) => formatVariableToComponent(variable, index)
            )
        }
    }

    const memoizedProps = useMemo(() => ({
        changeEditing: handleChangeEditing,
        isEditable,
        isEditing,
        tempValue,
        setTempGeneratedData,
        tempGeneratedData,
        setTempValue,
        loading,
        stepId,
        setLoading,
        stepItem,
        useSingleScreenshot,
        setUseSingleScreenshot
    }), [isEditing, isEditable, tempValue, loading, stepItem, stepId, tempGeneratedData, useSingleScreenshot])

    useEffect(() => {
        if (isEditing) {
            setTempValue(originalTitle)
            setUseSingleScreenshot(stepItem?.extra?.use_single_screenshot)
            // setError(undefined)
            setLoading(false)
        }

        if (!isEditing) {

            setTempValue(originalTitle)
            // setError(undefined)
            setLoading(false)

        }
    }, [isEditing]);

    const insertStep = useRunningStore((state) => state.insertStepAfter)
    
    const handleInsertStep = (stepType: EStepType) => {
        if (!stepItem?.localUUID) return
        insertStep(stepItem.localUUID, stepType)
    }

    const { t } = useTranslation()

    const insertMenu = (
        <Menu
            items={ [
                {
                    key: EStepType.STEP,
                    label: t('stepTypes.action'),
                    onClick: () => handleInsertStep(EStepType.STEP)
                },
                {
                    key: EStepType.RESULT,
                    label: t('stepTypes.expected_result'),
                    onClick: () => handleInsertStep(EStepType.RESULT)
                }
            ] }
        />
    )


    return (
        <SingleRunStepContext.Provider value={ memoizedProps }>
            <Flex
                align="flex-start"
                className={ stylesCSS.container }
                gap={ 10 }
                onClick={ handleClick }
                style={ { 
                    height: 'fit-content',
                    ...styles,
                    ...overrideStyle, 
                    ...disabledStyles 
                } }
                vertical
            >
                <Flex align="flex-start" gap={ 16 } style={ { width: '100%' } }>
                    {!noStatus && (
                        <StatusIndicator
                            count={ stepIndex }
                            // TODO: Временный костыль
                            isSharedStep={ !!props?.extra?.shared_step && stepType !== EStepType.RESULT }
                            loading={ isLoading }
                            status={ status }
                            { ...statusProps }
                        />
                    )}
                    <Flex
                        align="flex-start"
                        flex={ 1 }
                        gap={ 10 }
                        justify="space-between"
                        style={ { height: '100%', width: '100%', position: 'relative' } }
                        vertical
                    >

                        {isEditing
                            ? (
                                <div style={ { width: '100%' } }>
                                    <AutocompleteVariablesTextarea
                                        externalVariables={ formattedVariablesList }
                                        onChange={ handleChangeInput }
                                        projectId={ currentRun?.case?.project_id }
                                        value={ tempValue }
                                        variablesKitName={ currentRun?.case?.variables }
                                    />
                                    {!!currentError &&
                                    <Typography.Text type="danger">
                                        {typeof currentError === 'string' 
                                            ? currentError 
                                            : JSON.stringify(currentError)}
                                    </Typography.Text>}
                                </div>
                            ) : <Typography.Text
                                className={ cn(
                                    CLASSNAMES.testCaseStepName,
                                    CLASSNAMES.stepType(stepType),
                                    stylesCSS.title)
                                }
                            >
                                {formattedTitle()}
                            </Typography.Text>
                        }
                        {!!description && (
                            isString(description)
                                ? <Typography.Text style={ { color: token.colorTextDescription } }>
                                    {description}
                                </Typography.Text>
                                : description
                        )
                        }
                    </Flex>
                </Flex>
                <Flex
                    align="center"
                    flex={ 1 }
                    gap={ 16 }
                    justify="space-between"
                    style={ { height: '100%', width: '100%', position: 'relative' } }
                >
                    <div className={ stylesCSS.iconPlaceholder }>

                        {!!contextIcon && (
                            <ContextScreenshotIcon
                                disabled={ !stepItem.contextScreenshotMode?.isEnabled 
                                || stepItem?.status_step === ERunStatus.UNTESTED }
                                screenshotUrl={ stepItem?.extra?.context_screenshot_path?.url }
                                wrapStyles={ 
                                    { position: 'relative', inset: '0', marginBottom: 1 } }
                            />
                        )}
                    </div>

                    {isEditing ?
                        <EditModeActions
                            actionName={ actionName }
                            actionStyles={ getActionNameStyles() }
                            editActions={ editActions }
                            variablesList={ variableObject }
                        /> :
                        <ViewModeBottom
                            actionStyles={ getActionNameStyles() }
                            { ...props }
                        />
                    }
                </Flex>

                {/* Кнопка Insert в правом нижнем углу */}
                {canInsertStepAfter
                && <Dropdown
                    menu={ { items: insertMenu.props.items } }
                    placement="topRight"
                    trigger={ ['click'] }
                >
                    <Button
                        icon={ <PlusOutlined/> }
                        shape="circle"
                        size="small"
                        style={ {
                            position: 'absolute',
                            bottom: -10,
                            right: -8,
                            zIndex: 1
                        } }
                        title="Add step"
                        type="primary"
                    />
                </Dropdown>}
            </Flex>
        </SingleRunStepContext.Provider>
    )

}


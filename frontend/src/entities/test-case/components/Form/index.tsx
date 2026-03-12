import { EllipsisOutlined, PlusOutlined } from '@ant-design/icons';
import { AsyncSelect, StatusIndicator } from '@Common/components';
import { DraggableList } from '@Common/components/DraggableList';
import { IStep } from '@Common/types';
import { urlValidator } from '@Common/validators';
import { getSortableKey } from '@Components/DraggableList/utils.ts';
import { HighlightTextarea } from '@Components/HighlightTextarea';
import { DragDropProvider, KeyboardSensor, PointerSensor, } from '@dnd-kit/react';
import { IEnvironmentListItem } from '@Entities/environment';
import { envQueries } from '@Entities/environment/queries';
import { useProjectStore } from '@Entities/project/store';
import { EStepGroup } from '@Entities/runs/models';
import { ApiInput } from '@Entities/test-case/components/Form/components';
import { useMenuFeatures } from '@Entities/test-case/components/Form/menu.tsx';
import { EMenuActions, EStepType, IBaseForm } from '@Entities/test-case/components/Form/models';
import { ITempTestCaseFormSettings } from '@Entities/test-case/models';
import { caseQueries } from '@Entities/test-case/queries';
import { variableQueries } from '@Entities/variable/queries';
import { SharedStepSelect } from '@Features/shared-steps';
import { SuiteSelect } from '@Features/suite/suite-selects';
import { VariableKitSelect } from '@Features/variable/kit-select';
import { useQuery } from '@tanstack/react-query';
import {
    Button,
    Divider,
    Dropdown,
    Flex,
    Form,
    FormInstance,
    type FormListFieldData,
    type FormListOperation,
    FormProps,
    Input,
    Result,
    Select,
    Space,
    Spin,
    Typography
} from 'antd';
import { Rule } from 'antd/es/form';
import { List } from 'immutable';
import cloneDeep from 'lodash/cloneDeep';
import get from 'lodash/get';
import map from 'lodash/map';
import merge from 'lodash/merge';
import { Store } from 'rc-field-form/lib/interface';
import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import enTranslations from '../../../../locales/en/translation.json';
import { StepFormItem } from '../StepFormItem';

interface IProps<T> {
    isPending?: boolean
    initialValues?: Store
    isLoading?: boolean,
    form: FormInstance<T>
    formProps?: FormProps
    buttonsToolbar?: ReactNode
    isInitError?: boolean
    hiddenFields?: ReactNode
    initialExtraInfo?: Record<string, string>[]
    needForceUpdateAfterChangeInitial?: boolean
}

export interface IStepsConfig {
    key: EStepGroup;
    features: Array<EStepType>
}

const config = [
    {
        key: EStepGroup.BEFORE_BROWSER,
        features: [EStepType.API]
    },
    {
        key: EStepGroup.BEFORE,
        features: [EStepType.API, EStepType.STEP, EStepType.SHARED_STEP]
    },
    {
        key: EStepGroup.STEPS,
        features: [EStepType.API, EStepType.STEP, EStepType.RESULT, EStepType.SHARED_STEP]
    },
    {
        key: EStepGroup.AFTER,
        features: [EStepType.API, EStepType.STEP]
    }
] as IStepsConfig[]

const DEFAULT_INITIAL_VALUES = {
    variables: 'Default'
}

type TListTypes = 'steps' | 'before_steps' | 'after_steps' | 'before_browser_start'

export const TestCaseForm = <T extends IBaseForm, >
    ({
        isLoading,
        isPending,
        initialValues,
        isInitError,
        form,
        formProps,
        buttonsToolbar,
        hiddenFields,
        needForceUpdateAfterChangeInitial

    }: IProps<T>) => {
    const { t } = useTranslation()
    const navigate = useNavigate()
    const formTranslate = t('create_test_case', { returnObjects: true }) as typeof enTranslations['create_test_case'];
    const project = useProjectStore((state) => state.currentProject)
    const { featureClick, getMenu: getMenuHelper } = useMenuFeatures()
    const [apiRules, setApiRules] = useState<Rule[]>([])
    const allFormValues = Form.useWatch([], form);
    const [key, setKey] = useState(0)
    const formListOperations = useRef({} as Record<TListTypes, FormListOperation>);
    const formStepUpdateHandlers = useRef({} as Record<string, (data: any) => void>);
    
    const [tempSettings, setTempSettings] = useState<ITempTestCaseFormSettings>({
        alreadyShowWarningContextScreenshots: false
    })
    const { id } = useParams()
    const kitName = get(allFormValues, 'variables')

    const { data: variablesList } = useQuery(variableQueries.variableListByName({
        project_id: id!!,
        variables_kit_name: kitName!!,
    }, { enabled: !!kitName && !!id }))

    const formattedList = map(variablesList?.variables_details, (item) => item.variable_name ?? '')

    const getRules = (type: EStepType) => {
        switch (type) {
            case EStepType.API:
                return apiRules
            default:
                return []
        }
    }

    const handleUpdateFormItem = useCallback((itemName?: any, data?: any) => {
        const stepItem = form.getFieldValue(itemName) as IStep
        const mergedData = merge({}, stepItem, data)

        form.setFieldValue(itemName, mergedData)
    }, [form])

    const initialValuesWithDefault = useMemo(() => ({
        ...DEFAULT_INITIAL_VALUES,
        ...initialValues,
    }), [initialValues])

    const groupOffsets = useMemo(() => {
        const offsets = new Map<string, number>();
        let currentOffset = 0;

        if (allFormValues) {
            for (const group of config) {
                offsets.set(group.key, currentOffset);
                const stepsInGroup = allFormValues[group.key] || [];

                currentOffset += stepsInGroup.length;
            }
        }

        return offsets;
    }, [allFormValues]);

    /*
     * const validateDragNDrop = (group?: IStep[]) => {
     *     if (!group) return {
     *         success: true
     *     }
     *     let success = true
     *
     *     forEach(group, (step, index) => {
     *         if (step.type === EStepType.RESULT && index === 0) {
     *             const error = 'Cannot place a Expected Result step to first place'
     *
     *             message.error(error)
     *
     *             success = false
     *         }
     *         if (step.type === EStepType.SHARED_STEP) {
     *             if (group[index + 1] && group[index + 1].type === EStepType.RESULT) {
     *                 const error = 'Cannot place a Shared Step before a Result step.'
     *
     *                 message.error(error)
     *
     *                 success = false
     *             }
     *         }
     *     })
     *
     *     return {
     *         success
     *     }
     * }
     */

    const handleTempSettingsChange = (changedSettings: ITempTestCaseFormSettings) => {
        setTempSettings((prev) => ({
            ...prev,
            ...changedSettings
        }))
    }

    const handleDragEnd = (event: any) => {
        const { operation } = event || {}

        const { source, target } = operation || {}
        const formData = cloneDeep(form.getFieldsValue())

        const sourceStart = {
            index: source?.sortable.initialIndex,
            group: source?.data?.group,
        };

        const sourceFinish = {
            index: source?.sortable?.index,
            group: source?.sortable?.group,
        };

        // нужно, чтобы ререндерить форму, иначе dnd-kit с антовской формой работает хреново
        setKey((prev) => prev + 1)

        // если тип таргета колонка - то просто пушим элемент в конец массива
        if (target?.type === 'column') {

            // если находимся в той же группе
            if (sourceStart.group === target.id) return

            const prevGroup = List(formData[sourceStart.group])
            const nextGroup = List(formData[target.id])

            const prevUpdatedData = prevGroup.remove(sourceStart.index)
            const nextUpdatedData = nextGroup.push(prevGroup.toArray()[sourceStart.index])

            const updatedData = {
                ...formData,
                [sourceStart.group]: prevUpdatedData.toArray(),
                [target.id]: map(nextUpdatedData.toArray(), (step) => ({
                    //@ts-ignore
                    ...step,
                    stepGroup: target.id
                }))
            }

            //@ts-ignore
            form.setFieldsValue(updatedData)

            return
        }

        // если действуем в рамках одной группы
        if (sourceStart.group === sourceFinish.group) {
            formListOperations.current[sourceFinish.group as TListTypes]?.move(sourceStart.index, sourceFinish.index)

            return
        }

        // если просто перетаскиваем кейс из одной группы в другую
        try {
            const prevGroup = List(formData[sourceStart.group])
            const nextGroup = List(formData[sourceFinish.group])

            const prevUpdatedData = prevGroup.remove(sourceStart.index)
            const nextUpdatedData = nextGroup.insert(sourceFinish.index, prevGroup.toArray()[sourceStart.index])

            const updatedData = {
                ...formData,
                [sourceStart.group]: prevUpdatedData.toArray(),
                [sourceFinish.group]: map(nextUpdatedData.toArray(), (step) => ({
                    //@ts-ignore
                    ...step,
                    stepGroup: sourceFinish.group
                })),
            }

            //@ts-ignore
            form.setFieldsValue(updatedData)
        } catch (e) {
            console.error(`[DRAG_N_DROP_ERROR]: ${e}`)
        }


        return
    }

    if (isInitError) {
        return (
            <Result
                extra={
                    <Button onClick={ () => navigate('/') }>
                        {t('common.api_error')}
                    </Button>
                }
                status="warning"
                title={ t('common.api_error') }
            />
        )
    }

    useEffect(() => {
        if (initialValuesWithDefault && needForceUpdateAfterChangeInitial) {

            // @ts-ignore
            form.setFieldsValue(initialValuesWithDefault)

        }
    }, [initialValuesWithDefault, needForceUpdateAfterChangeInitial]);

    return (
        <Spin spinning={ isLoading }>
            {isPending && <Spin fullscreen/>}
            <Form<T>
                form={ form }
                initialValues={ initialValuesWithDefault }
                layout="vertical"
                scrollToFirstError={ {
                    behavior: 'smooth',
                } }
                style={ { display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' } }
                validateTrigger={ 'onBlur' }
                { ...formProps }
            >
                <Flex vertical>
                    {hiddenFields}
                    <Form.Item
                        label={ formTranslate.input_name.label }
                        name="name"
                        rules={ [{ required: true, message: t('errors.input.required') }] }
                    >
                        <Input placeholder={ formTranslate.input_name.placeholder }/>
                    </Form.Item>

                    <Form.Item
                        label={ formTranslate.description.label }
                        name="description"
                    >
                        <Input.TextArea placeholder={ formTranslate.description.placeholder }/>
                    </Form.Item>


                    <Form.Item
                        label={ formTranslate.select_suite.label }
                        name="suite_id"
                        rules={ [{ required: true, message: t('errors.input.required') }] }
                    >
                        <SuiteSelect/>
                    </Form.Item>

                    <Flex gap={ 16 } justify={ 'space-evenly' }>
                        <Form.Item
                            label={ t('create_test_case.select_execution_type.label') }
                            name="type"
                            style={ { flex: 1 } }
                        >
                            <AsyncSelect
                                labelTransform={ (label) => t(`caseTypes.${label}`) }
                                onLoadData={ (data) => {
                                    const initialValue = get(form.getFieldsValue(), 'type', '')

                                    if (!initialValue) {
                                        //@ts-ignore
                                        form.setFieldValue('type', data?.[0])
                                    }
                                } }
                                queryOptions={ caseQueries.caseTypes() }
                            />
                        </Form.Item>

                        <Form.Item
                            initialValue={ formTranslate.select_status.options[0].label }
                            label={ formTranslate.select_status.label }
                            name="status"
                            style={ { flex: 1 } }
                        >
                            <Select>
                                {map(formTranslate.select_status.options, (item, index) => (
                                    <Select.Option key={ index } value={ item.label }>
                                        {item.label}
                                    </Select.Option>
                                ))}
                            </Select>
                        </Form.Item>

                        <Form.Item
                            initialValue={ formTranslate.select_priority.options[0].label }
                            label={ formTranslate.select_priority.label }
                            name="priority"
                            style={ { flex: 1 } }
                        >
                            <Select>
                                {map(formTranslate.select_priority.options, (item, index) => (
                                    <Select.Option key={ index } value={ item.label }>
                                        {item.label}
                                    </Select.Option>
                                ))}
                            </Select>
                        </Form.Item>
                    </Flex>

                    <Form.Item
                        label={ t('variables.select.label') }
                        name="variables"
                        rules={ [{ required: true, message: t('errors.input.required') }] }
                    >
                        {project && <VariableKitSelect projectId={ project.project_id }/>}
                    </Form.Item>

                    <Form.Item
                        label={ t('environment.select.label') }
                        name="environment_id"
                    >
                        <AsyncSelect<IEnvironmentListItem>
                            defaultValue={ null }
                            keyIndex={ 'environment_id' }
                            labelIndex={ 'title' }
                            placeholder={ t('environment.select.placeholder') }
                            queryOptions={ envQueries.envList(id!) }
                            allowClear
                        />

                    </Form.Item>

                    <Form.Item
                        label={ formTranslate.input_url.label }
                        name="url"
                        rules={ [
                            { required: true, message: t('errors.input.required') },
                            urlValidator(t('errors.input.url')),
                        ] }
                    >
                        <Input placeholder={ formTranslate.input_url.placeholder }/>
                    </Form.Item>

                    <DragDropProvider
                        key={ key }
                        onDragEnd={ handleDragEnd }
                        sensors={ [
                            PointerSensor,
                            KeyboardSensor
                        ] }
                    >
                        {map(config, (item) => {
                            const offset = groupOffsets.get(item.key) || 0;
                            const listName = item.key

                            const draggableAccept = item.features

                            return <DraggableList
                                key={ listName }
                                accept={ draggableAccept }
                                name={ listName }>
                                {(fields, { add, remove, move }: FormListOperation, parentElement) => {
                                    if (!formListOperations.current[listName as unknown as TListTypes]) {
                                        formListOperations.current[listName as unknown as TListTypes] = {
                                            add,
                                            move,
                                            remove
                                        };
                                    }

                                    return (
                                        <Flex
                                            key={ `inner-list-${item.key}` }
                                            style={ { marginBottom: '22px', maxWidth: 656 } }
                                            vertical>
                                            <Divider
                                                orientation={ 'left' }
                                                orientationMargin={ 0 }
                                                style={ { marginBlock: `0px 8px` } }
                                            >
                                                <Typography.Text>{t(`stepGroups.${item.key}`)}</Typography.Text>
                                            </Divider>
                                            {map(fields, ({ key, name, ...restField }: FormListFieldData, index) => {
                                                
                                                const inputBaseName = [item.key, name]
                                                const joinedStepName = inputBaseName.join('_');

                                                //@ts-ignore
                                                const stepItem = form.getFieldValue(inputBaseName) as IStep

                                                if (!formStepUpdateHandlers?.current[joinedStepName]) {

                                                    formStepUpdateHandlers.current[joinedStepName] = (data: any) => {
                                                        handleUpdateFormItem(inputBaseName, data)
                                                    }
                                                }

                                                const update = formStepUpdateHandlers.current[joinedStepName];


                                                const type = stepItem.type ?? EStepType.STEP

                                                const { items: menuItems }
                                                    = getMenuHelper(
                                                        { 
                                                            stepTypes: item.features,
                                                            stepData: stepItem
                                                        })
                                                || {}

                                                const inputStyle = { maxWidth: 534 }

                                                let InputNode

                                                switch (type) {
                                                    case EStepType.API:
                                                        InputNode = <ApiInput
                                                            baseName={ inputBaseName }
                                                            form={ form }
                                                            getRules={ setApiRules }
                                                            style={ inputStyle }
                                                            variablesList={ formattedList || [] }
                                                        />
                                                        break

                                                    case EStepType.SHARED_STEP:
                                                        InputNode = (
                                                            <SharedStepSelect
                                                                onLoadData={ (data) => {
                                                                    const defaultStepId = data?.[0]?.shared_steps_id

                                                                    if (!stepItem?.step && defaultStepId) {
                                                                        handleUpdateFormItem(inputBaseName, {
                                                                            step: defaultStepId
                                                                        })
                                                                    }
                                                                } }/>
                                                        )
                                                        break
                                                    default:
                                                        InputNode = <HighlightTextarea
                                                            initialVariables={ formattedList || [] }
                                                            placeholder={
                                                                t(`create_test_case.placeholders.${type}`)
                                                            }
                                                            style={ { width: '100%', ...inputStyle } }
                                                        />
                                                        break
                                                }

                                                const actualIndex = offset + index

                                                const sortableAccept = draggableAccept
                                                const domId = `${listName}_${name}_step`

                                                return (
                                                    <DraggableList.Item
                                                        key={ [listName, key].join('-') }
                                                        accept={ sortableAccept }
                                                        domId={ domId }
                                                        group={ listName }
                                                        id={ getSortableKey({ prefix: listName, index: key }) }
                                                        index={ name }
                                                        itemData={ {
                                                            stepType: type
                                                        } }
                                                        parentElement={ parentElement }
                                                        style={ {
                                                            paddingBottom: 8
                                                        } }
                                                        type={ type }
                                                    >
                                                        <>
                                                            <StatusIndicator
                                                                count={ actualIndex + 1 }
                                                                elementStyle={ { marginTop: 4 } }
                                                                type={ type }
                                                            />

                                                            <StepFormItem
                                                                config={ tempSettings }
                                                                form={ form }
                                                                onConfigChange={ handleTempSettingsChange }
                                                                stepName={ inputBaseName }
                                                                { ...restField }
                                                                name={ [name, 'step'] }
                                                                rules={ [
                                                                    {
                                                                        required: true,
                                                                        message: t('errors.input.required')
                                                                    },
                                                                    ...getRules(type)
                                                                ] }
                                                                style={ { flex: 1 } }
                                                            >
                                                                {InputNode}
                                                            </StepFormItem>

                                                            <Dropdown
                                                                menu={ {
                                                                    items: menuItems,
                                                                    onClick: ({ key }) => featureClick({
                                                                        add,
                                                                        remove,
                                                                        form,
                                                                        updateStep: update,
                                                                        indexNumber: name,
                                                                        groupType: item.key as EStepGroup,
                                                                        actionType: key as EMenuActions
                                                                    })
                                                                } }
                                                                trigger={ ['click'] }
                                                                destroyPopupOnHide
                                                            >
                                                                <Button icon={ <EllipsisOutlined/> } type="text"/>
                                                            </Dropdown>
                                                        </>
                                                    </DraggableList.Item>
                                                )
                                            })}
                                            <Space size={ 'small' }>
                                                {map(item.features, (f) => {


                                                    return (
                                                        <Button
                                                            key={ `item-feature-${f}-${item.key}` }
                                                            icon={ <PlusOutlined/> }
                                                            onClick={ () => add({ type: f, stepGroup: item.key }) }
                                                            type={ 'text' }
                                                            variant={ 'link' }
                                                        >
                                                            {t(`stepTypes.${f}`)}
                                                        </Button>
                                                    )
                                                }
                                                )}
                                            </Space>
                                        </Flex>
                                    );
                                }}
                            </DraggableList>
                        })}
                    </DragDropProvider>
                </Flex>
                {buttonsToolbar}
            </Form>
        </Spin>
    )
}

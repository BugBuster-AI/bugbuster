import { EllipsisOutlined, PlusOutlined } from '@ant-design/icons';
import { StatusIndicator } from '@Common/components';
import { IStep } from '@Common/types';
import { DraggableList } from '@Components/DraggableList';
import { getSortableKey } from '@Components/DraggableList/utils.ts';
import { HighlightTextarea } from '@Components/HighlightTextarea';
import { DragDropProvider, KeyboardSensor, PointerSensor } from '@dnd-kit/react';
import { useMenuFeatures } from '@Entities/shared-steps/components/Form/menu.tsx';
import { StepFormItem } from '@Entities/test-case';
import { ApiInput } from '@Entities/test-case/components/Form/components';
import { EMenuActions, EStepType } from '@Entities/test-case/components/Form/models.ts';
import { ITempTestCaseFormSettings } from '@Entities/test-case/models';
import {
    Button,
    Divider,
    Dropdown,
    Flex,
    Form,
    type FormListFieldData,
    type FormListOperation,
    Input, Space,
    Typography
} from 'antd';
import { Rule } from 'antd/es/form';
import isEmpty from 'lodash/isEmpty';
import map from 'lodash/map';
import { ReactElement, ReactNode, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface ISharedStepFormValues {
    name: string;
    description?: string;
    steps: IStep[]
}

interface IProps {
    form: any;
    onFinish: (values: ISharedStepFormValues) => void;
    initialValues?: Partial<ISharedStepFormValues>;
    controlButtons?: ReactNode
}

const listName = 'steps'
const stepsFeatures = [EStepType.API, EStepType.STEP]

export const SharedStepForm = ({ form, controlButtons, onFinish, initialValues }: IProps): ReactElement => {
    const { t } = useTranslation();
    const [apiRules, setApiRules] = useState<Rule[]>([])
    const listOperations = useRef<FormListOperation>({} as unknown as FormListOperation)
    const { getMenu: getMenuHelper, featureClick } = useMenuFeatures()
    const [tempSettings, setTempSettings] = useState<ITempTestCaseFormSettings>({
        alreadyShowWarningContextScreenshots: false
    })

    const handleTempSettingsChange = (changedSettings: ITempTestCaseFormSettings) => {
        setTempSettings((prev) => ({
            ...prev,
            ...changedSettings
        }))
    }


    const formattedList = []

    const getRules = (type: EStepType) => {
        switch (type) {
            case EStepType.API:
                return apiRules
            default:
                return []
        }
    }

    const handleDragEnd = (event: any) => {
        const { operation } = event || {}

        const { source } = operation || {}

        const sourceStart = {
            index: source?.sortable.initialIndex,
            group: source?.data?.group,
        };

        const sourceFinish = {
            index: source?.sortable?.index,
            group: source?.sortable?.group,
        };

        if (sourceStart.group === sourceFinish.group) {
            listOperations?.current?.move(sourceStart.index, sourceFinish.index)

            return
        }

    }

    return (
        <Form<ISharedStepFormValues>
            form={ form }
            initialValues={ initialValues }
            layout="vertical"
            onFinish={ onFinish }
            style={ { display: 'flex', flexDirection: 'column', flex: 1 } }
            validateTrigger={ 'onBlur' }
        >
            <Form.Item
                label={ t('sharedStepsPage.form.name.label') }
                name="name"
                rules={ [{ required: true, message: t('errors.input.required') }] }
            >
                <Input placeholder={ t('sharedStepsPage.form.name.placeholder') }/>
            </Form.Item>

            <Form.Item
                label={ t('sharedStepsPage.form.description.label') }
                name="description"
            >
                <Input.TextArea placeholder={ t('sharedStepsPage.form.description.placeholder') }/>
            </Form.Item>

            <DragDropProvider
                onDragEnd={ handleDragEnd }
                sensors={ [
                    PointerSensor,
                    KeyboardSensor
                ] }
            >

                <DraggableList accept={ stepsFeatures } name={ 'steps' }>
                    {(fields, { add, remove, move }: FormListOperation, parentElement) => {

                        if (isEmpty(listOperations.current) || !listOperations?.current?.move) {
                            listOperations.current = {
                                add,
                                move,
                                remove
                            };
                        }

                        return (
                            <Flex
                                style={ { marginBottom: '22px', maxWidth: 656 } }
                                vertical>
                                <Divider
                                    orientation={ 'left' }
                                    orientationMargin={ 0 }
                                    style={ { marginBlock: `0px 8px` } }
                                >
                                    <Typography.Text>{t(`stepGroups.shared_steps`)}</Typography.Text>
                                </Divider>
                                {map(fields, ({ key, name, ...restField }: FormListFieldData, index) => {

                                    // @ts-ignore
                                    const type = form.getFieldValue([listName, name, 'type'])

                                    const { items } = getMenuHelper({ groupType: listName }) || {}

                                    const inputStyle = { maxWidth: 534 }
                                    const inputBaseName = [listName, name]

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

                                    return (
                                        <DraggableList.Item
                                            key={ [listName, key].join('-') }
                                            accept={ stepsFeatures }
                                            group={ listName }
                                            id={ getSortableKey({ prefix: listName, index: key }) }
                                            index={ name }
                                            itemData={ {
                                                stepType: type
                                            } }
                                            parentElement={ parentElement }
                                            style={ { paddingBottom: 8 } }
                                            type={ type }
                                        >
                                            <>
                                                <StatusIndicator
                                                    count={ index + 1 }
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
                                                        items,
                                                        onClick: ({ key }) => featureClick({
                                                            add,
                                                            remove,
                                                            form,
                                                            indexNumber: name,
                                                            groupType: listName,
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
                                    {map(stepsFeatures, (f) => (
                                        <Button
                                            key={ `item-feature-${f}-${listName}` }
                                            icon={ <PlusOutlined/> }
                                            onClick={ () => add({ type: f }) }
                                            type={ 'text' }
                                            variant={ 'link' }
                                        >
                                            {t(`stepTypes.${f}`)}
                                        </Button>
                                    )
                                    )}
                                </Space>
                            </Flex>
                        );
                    }}
                </DraggableList>
            </DragDropProvider>
            {controlButtons}
        </Form>
    )
}


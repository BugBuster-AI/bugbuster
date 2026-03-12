import { DeleteOutlined, LoadingOutlined } from '@ant-design/icons'
import { AppearanceAnimation } from '@Common/components/Animations/Appearance'
import { DraggableList } from '@Common/components/DraggableList'
import { useThemeToken } from '@Common/hooks'
import { DragDropProvider, KeyboardSensor, PointerSensor } from '@dnd-kit/react'
import { Button, Checkbox, Flex, Form, FormInstance, Input, Select, Spin, Typography } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { BASE_VARIABLES_LIST, FORMAT_LIST, SPECIAL_FORMATS, TIMEZONE_LIST } from '../consts'
import { useComputedValue } from './helper'

export interface IProps<T> {
    form: FormInstance<T>
    computedValue?: string | null
    isLoadingPreview?: boolean
    kitId: string
}

const FORM_NAMES = {
    TIME_SHIFTS: ['variable_config', 'shifts'],
    BASE_VARIABLE: ['variable_config', 'base'],
    TIMEZONE: ['variable_config', 'utc_offset'],
    FORMAT: ['variable_config', 'format'],
    IS_CONST: ['variable_config', 'is-const'],
    CUSTOM_FORMAT: 'customFormat',
}

export const TimeVariableSettings = <T,>(props: IProps<T>) => {
    const { t } = useTranslation('translation', { keyPrefix: 'variablesPage.details' })
    const form = props.form
    const { isLoading: isLoadingPreview, value: computedValue, error } = useComputedValue({ 
        kitId: props.kitId,
        form, 
        enabled: !!Form.useWatch(FORM_NAMES.BASE_VARIABLE, form)
    })

    const formOperations = useRef<{move: any} | null>(null)

    const TIME_UNIT_OPTIONS = [
        { label: t('timeShifts.units.seconds'), value: 'seconds' },
        { label: t('timeShifts.units.minutes'), value: 'minutes' },
        { label: t('timeShifts.units.hours'), value: 'hours' },
        { label: t('timeShifts.units.days'), value: 'days' },
        { label: t('timeShifts.units.months'), value: 'months' },
        { label: t('timeShifts.units.years'), value: 'years' }
    ]

    const timezoneValue = Form.useWatch(FORM_NAMES.TIMEZONE, form);
    const formatValue = Form.useWatch(FORM_NAMES.FORMAT, form);
    
    const [isUseFormat, setUseFormat] = useState(false)
    const [isUseTimezone, setUseTimezone] = useState(false)

    const token = useThemeToken()
  
    // Синхронизируем состояние чекбоксов с данными формы
    useEffect(() => {
        setUseFormat(!!formatValue)
    }, [formatValue]);

    useEffect(() => {
        setUseTimezone(!!timezoneValue)
    }, [timezoneValue]);

    /*
     * useEffect(() => {
     *     return () => {
     *         form.resetFields()
     *     }
     * }, [])
     */

    const isConst = Form.useWatch(FORM_NAMES.IS_CONST, form)
    const currentFormat = Form.useWatch(FORM_NAMES.FORMAT, form)

    const { baseVariables, formatsList, timezoneList } = useMemo(() => {
        return {
            baseVariables: Object.entries(BASE_VARIABLES_LIST(t)).map(([key, value]) => ({
                value: key,
                label: value
            })),
            formatsList: Object.entries(FORMAT_LIST()).map(([key, value]) => ({
                value: key,
                label: value
            })),
            timezoneList: Object.entries(TIMEZONE_LIST()).map(([key, value]) => ({
                value: key,
                label: value
            }))
        }
    }, [t])

    // Используем computed_value из API вместо мокового значения
    const previewString =  ((computedValue && !error)
        ? `${computedValue}${isConst ? ` ${t('constantSuffix')}` : ''}`
        : '-')
    

    const handleChangeFormatUsage = (checked: boolean) => {
        setUseFormat(checked)

        if (!checked) {
            // Очищаем оба поля при снятии галочки
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            form.setFieldValue(FORM_NAMES.FORMAT as any, undefined)
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            form.setFieldValue(FORM_NAMES.CUSTOM_FORMAT as any, undefined)
        }
    }

    const handleChangeTimezoneUsage = (checked: boolean) => {
        setUseTimezone(checked)

        if (!checked) {
            form.setFieldValue(FORM_NAMES.TIMEZONE as any, undefined)
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

        formOperations.current?.move(sourceStart.index, sourceFinish.index)
    }

    return (
        <Flex vertical>
            <Form.Item
                label={ t('baseVariable') }
                name={ FORM_NAMES.BASE_VARIABLE }
                rules={ [{ required: true, message: t('validation.required') }] }   
                style={ { marginBottom: 18 } }
            >
                <Select options={ baseVariables } placeholder={ t('baseVariablePlaceholder') } />
            </Form.Item>

            <Typography.Text style={ { marginTop: 0 } }>
                {t('timeShifts.title')}
            </Typography.Text>

            <DragDropProvider
                onDragEnd={ handleDragEnd }
                sensors={ [
                    PointerSensor,
                    KeyboardSensor
                ] }
            >
                <DraggableList
                    accept="timeshift-item"
                    enableDropTarget={ false } 
                    name={ FORM_NAMES.TIME_SHIFTS }
                    style={ { padding: 0, marginBottom: 4 } }
                    type="timeshift-column"
                >
                    {(fields, { add, remove, move }) => {
                        formOperations.current = { move }

                        return (<>
                            {fields.map((field, index) => (
                                <DraggableList.Item
                                    key={ field.key }
                                    accept="timeshift-item"
                                    dataType="timeshift-item"
                                    id={ field.key }
                                    index={ index }
                                    style={ { marginTop: 8 } }
                                    type="timeshift-item"
                                >
                                    <Flex gap={ 8 } style={ { flex: 1 } }>
                                        <Form.Item
                                            name={ [field.name, 'value'] }
                                            rules={ [
                                                { required: true, message: t('timeShifts.validation.valueRequired') }
                                            ] }
                                            style={ { marginBottom: 0, width: 120 } }
                                        >
                                            <Input placeholder={ t('timeShifts.valuePlaceholder') } type="number" />
                                        </Form.Item>

                                        <Form.Item
                                            name={ [field.name, 'type'] }
                                            rules={ [
                                                { required: true, message: t('timeShifts.validation.typeRequired') }
                                            ] }
                                            style={ { marginBottom: 0, flex: 1 } }
                                        >
                                            <Select
                                                options={ TIME_UNIT_OPTIONS }
                                                placeholder={ t('timeShifts.typeLabel') }
                                            />
                                        </Form.Item>

                                        <Button
                                            danger={ true }
                                            icon={ <DeleteOutlined /> }
                                            onClick={ () => remove(field.name) }
                                            type="text"
                                        />
                                    </Flex>
                                </DraggableList.Item>
                            ))}

                            <Button
                                color="green"
                                onClick={ () => add({ value: '', type: 'seconds' }) }
                                style={ { marginBlock: `8px 18px` } }
                                type="dashed"
                                variant="solid"
                            >
                                {t('timeShifts.addButton')}
                            </Button>
                        </>)}
                    }
                </DraggableList>
            </DragDropProvider>

            <AppearanceAnimation
                style={ { marginBottom: 12 } }
                trigger={ (
                    <Checkbox
                        checked={ isUseTimezone }
                        onChange={ (e) => handleChangeTimezoneUsage(e.target.checked) } 
                    >
                        {t('useTimezone')}
                    </Checkbox>
                ) }
                visible={ isUseTimezone }
                saveInDom
            >
                <Form.Item
                    name={ FORM_NAMES.TIMEZONE }
                    rules={ isUseTimezone ? [{ required: true, message: t('validation.required') }] : [] }
                    style={ { marginBlock: `8px 0px` } }
                >
                    <Select options={ timezoneList } placeholder={ t('selectTimezone') } />
                </Form.Item>
            </AppearanceAnimation>

            <AppearanceAnimation
                style={ { marginBottom: 12 } }
                trigger={ (
                    <Checkbox
                        checked={ isUseFormat }
                        onChange={ (e) => handleChangeFormatUsage(e.target.checked) } 
                    >
                        {t('useFormat')}
                    </Checkbox>
                ) }
                visible={ isUseFormat }
                saveInDom
            >
                <Form.Item
                    name={ FORM_NAMES.FORMAT }
                    rules={ isUseFormat ? [{ required: true, message: t('validation.required') }] : [] }
                    style={ { marginBlock: `8px 0px` } }
                >
                    <Select options={ formatsList } placeholder={ t('selectFormat') } />
                </Form.Item>
                {currentFormat === SPECIAL_FORMATS.CUSTOM_FORMAT && (
                    <Form.Item
                        name={ FORM_NAMES.CUSTOM_FORMAT }
                        rules={ [{ required: true, message: t('validation.required') }] }
                        style={ { marginBlock: `8px 0px` } }
                    >
                        <Input placeholder={ t('customFormatPlaceholder') } />
                    </Form.Item>
                )}
            </AppearanceAnimation>
            
            <Form.Item name={ FORM_NAMES.IS_CONST } valuePropName="checked" noStyle>
                <Checkbox  style={ { marginBottom: 8 } } >{t('calculateOnce')}</Checkbox>
            </Form.Item>

            <Typography.Text style={ { fontSize: 12 } } type="secondary">
                {t('calculateOnceDescription')}
            </Typography.Text>

            <Spin 
                indicator={ <LoadingOutlined style={ { color: token.colorPrimary } } /> }
                spinning={ isLoadingPreview }
            >
                <Flex
                    gap={ 6 }
                    style={ {
                        borderRadius: 6, 
                        border: `1px solid ${token.colorPrimaryBorder}`, 
                        marginBlock: 18, 
                        background: token.colorPrimaryBg,
                        padding: 12,
                    } }
                    vertical
                >
                    <Typography style={ { color: token.colorPrimaryText } }>{t('preview')}</Typography>

                    <Typography.Text style={ { color: token.colorPrimaryText } }>
                        {previewString}
                    </Typography.Text>
                </Flex>
            </Spin>
        </Flex>
    )
}

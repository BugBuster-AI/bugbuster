import { AppearanceAnimation } from '@Common/components/Animations/Appearance';
import { TextWithTooltip } from '@Components/TextWithTooltip';
import {
    ICalculatedTariffPlans,
    ICreateCorporateInvoicePayload
} from '@Entities/billing/models';
import { useIssueInvoice } from '@Features/billing/payment-handlers/issue-invoice.tsx';
import { useIndividualPayment } from '@Features/billing/payment-handlers/pay-by-card.tsx';
import { TeamPlan } from '@Features/billing/upgrade-plan/components/TeamPlan';
import { useBuyStreamsContext } from '@Features/billing/upgrade-plan/context';
import { activePlanData, activePlanMonths, getPlanItems, getTooltipText } from '@Features/billing/upgrade-plan/helpers';
import { Button, Divider, Flex, Form, Input, InputNumber, Spin, Typography } from 'antd';
import debounce from 'lodash/debounce';
import get from 'lodash/get';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IForm {
    stream_count: number;
    promocode: string;
    inn: string;
    name: string
    kpp: string;
    variant?: string
}


export const CorporatePlan = () => {
    const { t } = useTranslation()
    const [activePlan, setActivePlan] = useState('0')
    const { handle: invoiceHandler, isPending: invoicePending } = useIssueInvoice()
    const { handle: paymentHandler, isPending: paymentPending } = useIndividualPayment()

    const {
        currentTariffData,
        tariffName,
        totalPriceLoading,
        isLoading,
        calculatedData,
        calculatedParams,
        setCalculatedParams,
        isYearly
    } = useBuyStreamsContext()


    const items = getPlanItems(t, calculatedData)
    const [form] = Form.useForm<IForm>()

    const streamCount = Form.useWatch('stream_count', form)
    const promocode = Form.useWatch('promocode', form)

    useEffect(() => {
        const debouncedHandler = debounce(() => {
            setCalculatedParams({
                promocode,
                stream_count: Number(streamCount)
            });
        }, 500);

        debouncedHandler();

        return () => {
            debouncedHandler.cancel();
        };
    }, [streamCount, promocode, setCalculatedParams]);

    const handlePayment = async () => {
        const data = form.getFieldsValue()

        try {
            await form.validateFields()
            await paymentHandler({
                stream_count: data.stream_count,
                promocode: data?.promocode,
                stream_only: false,
                cnt_months: activePlanMonths[activePlan],
                tariff_id: calculatedData?.tariff_id
            }, form)
        } catch (e) {
            console.error(e)
        }
    }

    const onSubmit = async () => {
        const data = form.getFieldsValue()

        try {
            await invoiceHandler({
                ...data,
                cnt_months: activePlanMonths[activePlan],
                tariff_id: calculatedData?.tariff_id
            } as ICreateCorporateInvoicePayload, form)

        } catch (e) {
            console.error(e)
        }
    }

    const tooltipText = getTooltipText(currentTariffData, t('buy_streams.teamPlan.title'))

    const currentActivePlan = activePlanData[activePlan]
    const currentCalculatedData: ICalculatedTariffPlans['yearly'] = get(calculatedData, currentActivePlan, undefined)


    useEffect(() => {
        if (isYearly) {
            setActivePlan('1')
        }
    }, [isYearly]);


    return (
        <Form<IForm>
            form={ form }
            initialValues={ calculatedParams }
            layout={ 'vertical' }
            onFinish={ onSubmit }
            style={ { marginTop: 16 } }
            clearOnDestroy>
            <Form.Item name={ 'variant' } style={ { marginBottom: 16 } }>
                <Flex gap={ 8 } vertical>
                    <Spin spinning={ isLoading }>
                        <div style={ { marginBottom: 4 } }>
                            <TextWithTooltip
                                text={
                                    <strong>
                                        {tariffName || calculatedData?.tariff_full_name || calculatedData?.tariff_name}
                                    </strong> }
                                tooltipProps={ {
                                    placement: 'right',
                                } }
                                tooltipTitle={ tooltipText }
                            />
                        </div>
                        <TeamPlan activeKey={ activePlan } items={ items } onChange={ setActivePlan }/>
                    </Spin>
                </Flex>
            </Form.Item>
            <Form.Item
                label={ t('buy_streams.name') }
                name={ 'name' }
                rules={ [{ required: true, message: t('errors.input.required') },] }>
                <Input/>
            </Form.Item>
            <Form.Item
                label={ t('buy_streams.additionalStreams') }
                name={ 'stream_count' }
                style={ { marginBottom: 16 } }>
                <InputNumber
                    min={ 0 }
                    onKeyDown={ (e) => {
                        // Блокируем ввод букв и символов, кроме цифр и управляющих клавиш
                        if (
                            // Разрешаем: цифры, Backspace, Delete, Tab, стрелки
                            !/[0-9]/.test(e.key) &&
                            !['Backspace', 'Delete', 'Tab', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown']
                                .includes(e.key)
                        ) {
                            e.preventDefault();
                        }
                    } }
                    placeholder={ '0' }
                    style={ { width: '100%' } }/>
            </Form.Item>
            <Form.Item
                label={ t('buy_streams.inn') }
                name={ 'inn' }
                rules={ [
                    { required: true, message: t('errors.input.required') },
                    {
                        pattern: /^(?:.{10}|.{12})$/,
                        message: t('errors.input.inn')
                    }
                ] }
                style={ { marginBottom: 16 } }>
                <Input/>
            </Form.Item>
            <Form.Item
                label={ t('buy_streams.kpp') }
                name={ 'kpp' }
                rules={ [
                    { required: true, message: t('errors.input.required') },
                    {
                        pattern: /^\d{9}$/,
                        message: t('errors.input.kpp')
                    }
                ] }
                style={ { marginBottom: 16 } }>
                <Input/>
            </Form.Item>
            <Form.Item label={ t('buy_streams.promo') } name={ 'promocode' } style={ { marginBottom: 16 } }>
                <Input placeholder={ 'XXX-XXXX' }/>
            </Form.Item>

            <Spin spinning={ totalPriceLoading }>
                <Flex gap={ 4 } vertical>
                    <Typography.Text>{t('buy_streams.summary.title')}</Typography.Text>

                    <Flex vertical>
                        <Flex className={ 'text-12' } justify={ 'space-between' }>
                            <Typography.Text
                                style={ { fontSize: '12px' } }
                                type={ 'secondary' }
                                strong
                            >
                                {tariffName || calculatedData?.tariff_full_name}
                            </Typography.Text>
                            <Typography.Text>
                                {currentCalculatedData?.price} {currentCalculatedData?.cur}
                            </Typography.Text>
                        </Flex>
                        <Flex
                            className={ 'text-12' }
                            justify={ 'space-between' }>
                            <Typography.Text
                                style={ { fontSize: '12px' } }
                                type={ 'secondary' }
                                strong
                            >
                                {t('buy_streams.summary.additionalTotal')}
                            </Typography.Text>
                            <Typography.Text>
                                {currentCalculatedData?.streams_price} {currentCalculatedData?.cur}
                            </Typography.Text>
                        </Flex>
                        <AppearanceAnimation visible={ !!currentCalculatedData?.discount_percent }>
                            <Flex
                                className={ 'text-12' }
                                justify={ 'space-between' }
                            >
                                <Typography.Text
                                    style={ { fontSize: '12px' } }
                                    type={ 'secondary' }
                                    strong
                                >
                                    {t('buy_streams.summary.discount')}
                                </Typography.Text>
                                <Typography.Text
                                    type={ 'success' }>
                                    -{currentCalculatedData?.discount_amount} {currentCalculatedData?.cur}
                                </Typography.Text>
                            </Flex>
                        </AppearanceAnimation>
                    </Flex>
                </Flex>
                <Divider style={ { margin: '12px 0' } }/>
                <Flex justify={ 'space-between' } style={ { paddingBottom: 16 } }>
                    <Typography.Text strong>{t('buy_streams.summary.total')}</Typography.Text>
                    <Typography.Text
                        strong>{currentCalculatedData?.total} {currentCalculatedData?.cur}</Typography.Text>
                </Flex>
            </Spin>
            <Flex gap={ 8 } justify={ 'flex-end' } style={ { paddingTop: 10 } }>
                <Button
                    loading={ invoicePending || paymentPending }
                    onClick={ handlePayment }
                >
                    {t('buy_streams.paymentByCard')}
                </Button>

                <Button
                    htmlType={ 'submit' }
                    loading={ invoicePending || paymentPending }
                    type={ 'primary' }
                >
                    {t('buy_streams.ok')}
                </Button>
            </Flex>
        </Form>
    )
}

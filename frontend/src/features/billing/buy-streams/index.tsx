import { getErrorMessage } from '@Common/utils/getErrorMessage.ts';
import { ETariffName, IGetAdditionalStreamsParams } from '@Entities/billing/models';
import { billingQueries } from '@Entities/billing/queries';
import { useIssueInvoice } from '@Features/billing/payment-handlers/issue-invoice.tsx';
import { useIndividualPayment } from '@Features/billing/payment-handlers/pay-by-card.tsx';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Button, Flex, Form, Input, InputNumber, Modal, Result, Segmented, Spin, Typography } from 'antd';
import debounce from 'lodash/debounce';
import isNil from 'lodash/isNil';
import { ReactElement, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IForm {
    stream_count: number;
    promocode?: string
    inn?: string;
    kpp?: string;
    name?: string
}

interface IProps {
    renderButton?: ({ open, onClick }: { open: boolean, onClick: () => void }) => ReactElement
}

export const BuyStreams = ({ renderButton }: IProps) => {
    const { t } = useTranslation()
    const [currentPlan, setCurrentPlan] = useState<ETariffName>(ETariffName.INDIVIDUAL)
    const [calculateParams, setCalculateParams] = useState<IGetAdditionalStreamsParams>({
        promocode: '',
        stream_count: 1
    })
    const [showError, setShowError] = useState('')
    const { handle: invoiceHandler, isPending: invoicePending } = useIssueInvoice()
    const { handle: paymentHandler, isPending: paymentPending } = useIndividualPayment()
    const [open, setOpen] = useState(false)
    const [mounted, setMounted] = useState(false)
    const [form] = Form.useForm<IForm>()

    const streamCount = Form.useWatch('stream_count', form)
    const promocode = Form.useWatch('promocode', form)

    useEffect(() => {
        const debouncedHandler = debounce(() => {
            setCalculateParams({
                promocode,
                stream_count: Number(streamCount)
            });
        }, 500);

        debouncedHandler();

        return () => {
            debouncedHandler.cancel();
        };
    }, [streamCount, promocode, setCalculateParams]);


    const {
        data,
        isLoading,
        error,
    } = useQuery(billingQueries.additionalStreams({
        ...calculateParams
    }, {
        placeholderData: keepPreviousData,
        enabled: !!calculateParams?.stream_count && open,
    }))
    
    useEffect(() => {
        if (error) {
            const msg = getErrorMessage({ error, needConvertResponse: true }) || 'Error'

            setShowError(msg)
        }
    }, [error]);

    useEffect(() => {
        if (!mounted && data) {
            setMounted(true)
        }
    }, [data]);

    const handleOpen = () => {
        setOpen(true)
    }

    const handleClose = () => {
        setOpen(false)
    }

    const handleInvoice = async () => {
        const formData = form.getFieldsValue()

        try {
            await form.validateFields()
            await invoiceHandler({
                stream_only: true,
                ...formData
            }, form)

            handleClose()
        } catch (e) {
            console.error(e)
        }
    }

    const handleCardPay = async () => {
        const formData = form.getFieldsValue()

        try {
            await form.validateFields()
            await paymentHandler({
                stream_only: true,
                stream_count: formData.stream_count,
                promocode: formData?.promocode
            }, form)

            handleClose()
        } catch (e) {
            console.error(e)
        }
    }

    const options = [{
        label: t('buy_streams.individual'),
        value: ETariffName.INDIVIDUAL,
    }, {
        label: t('buy_streams.corporate'),
        value: ETariffName.CORPORATE
    }]

    return <>
        {renderButton ?
            renderButton({ open, onClick: handleOpen }) :
            <Button onClick={ handleOpen } type={ 'primary' }>{t('workspace.billing.info.buy')}</Button>
        }
        <Modal
            cancelText={ t('buy_streams.paymentByCard') }
            footer={ null }
            okText={ t('buy_streams.ok') }
            onCancel={ handleClose }
            open={ open }
            title={ t('buy_streams.buy_streams_title') }
            centered
            destroyOnClose
        >
            {showError ? <Result status={ 'error' }>{showError}</Result>
                : <>
                    <Segmented
                        className={ 'segmented-full-width' }
                        defaultValue={ ETariffName.INDIVIDUAL }
                        onChange={ setCurrentPlan }
                        options={ options }
                        style={ {
                            marginBlock: '12px 16px'
                        } }
                        value={ currentPlan }
                    />
                    <Form<IForm>
                        form={ form }
                        initialValues={ {
                            stream_count: 1
                        } }
                        layout={ 'vertical' }
                        clearOnDestroy
                    >

                        {currentPlan === ETariffName.CORPORATE && <>
                            <Form.Item
                                label={ t('buy_streams.name') }
                                name={ 'name' }
                                rules={ [{ required: true, message: t('errors.input.required') },] }>
                                <Input/>
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
                        </>
                        }
                        <Form.Item
                            label={ t('buy_streams.streamCount') }
                            name={ 'stream_count' }
                            rules={ [
                                { required: true, message: t('errors.input.required') }
                            ] }
                            style={ { marginBottom: 16 } }
                        >
                            <InputNumber
                                min={ 1 }
                                onKeyDown={ (e) => {
                                    if (
                                        !/[0-9]/.test(e.key) &&
                                            !['Backspace', 'Delete',
                                                'Tab', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown']
                                                .includes(e.key)
                                    ) {
                                        e.preventDefault();
                                    }
                                } }
                                placeholder={ '0' }
                                style={ { width: '100%' } }/>
                        </Form.Item>
                        <Form.Item label={ t('buy_streams.promo') } name={ 'promocode' } style={ { marginBottom: 16 } }>
                            <Input placeholder={ 'XXX-XXXX' }/>
                        </Form.Item>
                        <Spin spinning={ isLoading }>
                            <Flex justify={ 'space-between' } style={ { paddingBottom: 16 } }>
                                <Typography.Text strong>{t('buy_streams.payment')}</Typography.Text>
                                {!isNil(streamCount) ?
                                    <Typography.Text
                                        strong>
                                        {data?.total_cost} {data?.cur || ''}
                                    </Typography.Text> :
                                    mounted &&
                                        <Typography.Text
                                            type={ 'danger' }>{t('errors.streams.input_count')}</Typography.Text>}
                            </Flex>
                        </Spin>
                        <Flex gap={ 8 } justify={ 'flex-end' } style={ { paddingTop: 10 } }>
                            {currentPlan === ETariffName.INDIVIDUAL ?
                                <Button
                                    htmlType={ 'button' }
                                    loading={ invoicePending || paymentPending }
                                    onClick={ handleCardPay }
                                    type={ 'primary' }
                                >
                                    {t('buy_streams.paymentByCard')}
                                </Button>
                                :
                                <Button
                                    htmlType={ 'button' }
                                    loading={ invoicePending || paymentPending }
                                    onClick={ handleInvoice }
                                    type={ 'primary' }
                                >
                                    {t('buy_streams.ok')}
                                </Button>
                            }
                        </Flex>
                    </Form>
                </>
            }
        </Modal>
    </>
}

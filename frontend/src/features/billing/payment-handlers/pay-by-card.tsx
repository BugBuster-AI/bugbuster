import { asyncHandler } from '@Common/utils';
import {
    ICreateIndividualPaymentPayload, ICreateIndividualPaymentResponse
} from '@Entities/billing/models';
import { useCreateIndividualPayment } from '@Entities/billing/queries/mutations.ts';
import { FormInstance, message } from 'antd';

export const useIndividualPayment = () => {
    const createPayment = useCreateIndividualPayment()

    const handle = async (data: ICreateIndividualPaymentPayload, form: FormInstance) => {
        await asyncHandler(createPayment.mutateAsync.bind(null, data), {
            successMessage: null,
            onSuccess: (response: ICreateIndividualPaymentResponse) => {
                if (!response?.Success) {
                    message.error(`Error: ${response.ErrorCode}`)
                } else if (response.Success && response.PaymentURL) {
                    window.open(response.PaymentURL, '_blank')
                }
            },
            onErrorValidate: ({ msg, field }) => {
                if (field && form) {
                    form.setFields([{
                        //@ts-ignore
                        name: String(field),
                        errors: [msg]
                    }])
                }
            }
        })
    }

    return {
        ...createPayment,
        handle
    }
}

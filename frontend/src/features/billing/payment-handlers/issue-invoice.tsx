import { asyncHandler } from '@Common/utils';
import { ICreateCorporateInvoicePayload, ICreateCorporateInvoiceResponse } from '@Entities/billing/models';
import { useCreateCorporateInvoice } from '@Entities/billing/queries/mutations.ts';
import { FormInstance, message } from 'antd';
import parse from 'html-react-parser';
import { useTranslation } from 'react-i18next';

export const useIssueInvoice = () => {
    const { t } = useTranslation()
    const createInvoice = useCreateCorporateInvoice()

    const handle = async (data: ICreateCorporateInvoicePayload, form: FormInstance) => {
        await asyncHandler(createInvoice.mutateAsync.bind(null, data), {
            successMessage: null,
            onSuccess: (response: ICreateCorporateInvoiceResponse) => {
                if (response?.errorDetails?.message) {
                    message.warning(parse(response?.errorDetails?.message))
                } else if (response?.pdfUrl) {
                    message.success(t('buy_streams.invoiceIssued'))
                    window.open(response?.pdfUrl, '_blank')
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
        ...createInvoice,
        handle
    }
}

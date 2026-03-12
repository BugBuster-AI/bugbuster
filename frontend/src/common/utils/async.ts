import { IApiErrorDetail, IError } from '@Common/types';
import { FormInstance, message, Modal } from 'antd';
import { ConfirmDialogProps } from 'antd/es/modal/ConfirmDialog';
import { AxiosError } from 'axios';
import forEach from 'lodash/forEach';
import last from 'lodash/last';
import map from 'lodash/map';

interface IOptions<T> {
    onError?: (error: IError | IApiErrorDetail, fullError: unknown) => void;
    onSuccess?: (value: T) => void;
    onFinally?: () => void;
    errorMessage?: string | null;
    successMessage?: string | null;
    confirm?: boolean
    confirmProps?: ConfirmDialogProps
    onErrorValidate?: ({ field, msg }: { field?: string, msg: string }) => void
    t?: (val: string) => string,
    formValidate?: {
        formInstance: FormInstance,
        transformFields?: Record<string, string>
    }
}

export const asyncHandler = async <T, >(cb: () => Promise<T>, options?: IOptions<T>) => {
    const {
        onError,
        errorMessage,
        successMessage,
        onSuccess,
        onFinally,
        confirm,
        confirmProps,
        t,
        onErrorValidate,
        formValidate
    } = options || {};
    const makeRequest = async () => {
        let response: T | null = null;

        try {
            const t = await cb();

            onSuccess && onSuccess(t as T);
            if (successMessage !== null) {
                message.success(successMessage || 'Success');
            }
            response = t;
        } catch (e) {
            const error = e as AxiosError;
            const errorResponse = error.response?.data as IError | IApiErrorDetail;

            const detail = errorResponse?.detail

            if (!detail && errorMessage !== null && !formValidate?.formInstance) {
                message.error(errorMessage || 'Failed to fetch')
            }

            if (typeof detail === 'string') {
                if (errorMessage !== null) {
                    message.error(detail)
                }
            } else {
                if (formValidate?.formInstance) {

                    const fields = map(detail, (item) => {
                        const lastField = last(item?.loc) || '';
                        let field = lastField;

                        if (formValidate?.transformFields) {
                            field = formValidate?.transformFields?.[lastField] || lastField;
                        }

                        return {
                            name: field,
                            errors: [item?.msg || '']
                        }
                    })

                    formValidate.formInstance.setFields(fields)

                    return
                }

                forEach(detail, (item) => {
                    const lastField = last(item?.loc)

                    onErrorValidate && onErrorValidate({ field: lastField, msg: item?.msg })
                    if (errorMessage !== null) {
                        message.error(item?.msg)
                    }
                })
            }

            onError && onError(errorResponse, e);
            throw e
        } finally {
            onFinally && onFinally();
        }

        return response
    }

    if (confirm) {
        const info = t ? {
            title: t('common.delete_title'),
            okText: t('common.confirm'),
            cancelText: t('common.cancel'),
            content: t('common.confirm_text')
        } : {}

        Modal.confirm({
            onOk: makeRequest,
            centered: true,
            icon: null,
            closable: true,
            content: 'Are you sure?',
            maskClosable: true,
            ...info,
            ...confirmProps
        })

        return
    }

    return await makeRequest()
};

import { TranslationType } from '@Common/types';

export const RETRY_CONFIG = {
    MAX_TIMEOUT: 60,
    WARNING_TIMEOUT: 45,
}
export const retryValidator = (t: TranslationType, value: any) => {
    if (!value) return Promise.resolve();
    if (value > RETRY_CONFIG.MAX_TIMEOUT) {
        return Promise.reject(
            new Error(t('environment.retry.error.maxTimeout'))
        );
    }

    return Promise.resolve();
}

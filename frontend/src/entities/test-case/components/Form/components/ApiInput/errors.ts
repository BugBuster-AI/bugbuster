import { ECurlValidationErrors } from '@Entities/test-case/components/Form/components/ApiInput/enums.ts';

export class CurlValidationError extends Error {
    public readonly type = ECurlValidationErrors.INVALID_CURL;

    constructor (message: string, public data?: any) {
        super(message);
        this.name = 'CurlValidationError';

        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, CurlValidationError);
        }
    }
}

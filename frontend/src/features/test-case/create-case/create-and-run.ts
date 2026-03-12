import { PATHS } from '@Common/consts';
import { asyncHandler } from '@Common/utils';
import { TestCaseApi } from '@Entities/test-case/api';
import { NavigateFunction } from 'react-router-dom';

interface IProps {
    caseId: string
    t: (val: string) => string,
    navigate?: NavigateFunction
}

const caseApi = TestCaseApi.getInstance()

export const createAndRun = async ({ navigate, caseId, t }: IProps) => {
    await asyncHandler(caseApi.runCase.bind(null, caseId), {
        errorMessage: t('common.api_error'),
        successMessage: null,
        onSuccess: (data) => {
            if (navigate) {
                navigate(PATHS.RUNNING.ABSOLUTE(data?.run_id!!))
            }
        }
    })
}

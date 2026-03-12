import { toFormData } from '@Entities/variable/components/VariableForm/adapters';
import { IVariable } from '@Entities/variable/models';

export const getLocalFormValues = (data?: IVariable): ReturnType<typeof toFormData> | Record<string, never> => {
    if (!data) {
        return {}
    }

    return toFormData(data)
}

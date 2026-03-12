import { useCurlEditFormContext } from '@Entities/test-case/components/Form/components/CurlEditForm/context/index.tsx';

export const useCurlEditFormDataSelector = () => {
    const { formData, setHeaders, setBody, setUrl, setValidation, setParams, setVariables } = useCurlEditFormContext()

    return { setHeaders, setBody, setUrl, setValidation, setParams, setVariables, ...formData }
}

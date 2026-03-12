import { IVariable } from '@Entities/variable/models';
import { usePrecalcVariable } from '@Entities/variable/queries';
import { Form } from 'antd';
import { FormInstance } from 'antd/lib';
import { useEffect, useState } from 'react';
import { toHttpData } from '../adapters';

interface IProps {
    form: FormInstance
    kitId: string
    enabled?: boolean
}
export const useComputedValue = (data: IProps) => {
    const { mutateAsync: precalcVariable, error } = usePrecalcVariable()
    const [computedValue, setComputedValue] = useState<string | null>(null)
    const [isLoadingPreview, setIsLoadingPreview] = useState(false)
    const { form, kitId } = data || {}
    const formValues = Form.useWatch([], form)

    // Debounce механизм для вызова precalc API
    useEffect(() => {
        if (!formValues || !form || !data.enabled) return
    
        const timer = setTimeout(async () => {
            try {
                const formData = form.getFieldsValue()
                    
                setIsLoadingPreview(true)
                const httpData = toHttpData(formData)
                
                // Вызываем precalc API
                const result = await precalcVariable(
                    {
                        ...httpData, 
                        variables_kit_id: kitId
                    } as Omit<IVariable, 'computed_value'>
                )
                    
                setComputedValue(result.computed_value)
            } catch (error) {
                // Игнорируем ошибки валидации
                console.error('Preview calculation error:', error)
            } finally {
                setIsLoadingPreview(false)
            }
        }, 500) // 500ms debounce
    
        return () => clearTimeout(timer)
    }, [formValues, form, precalcVariable])
        
    return {
        isLoading: isLoadingPreview,
        value: computedValue,
        error
    }
}

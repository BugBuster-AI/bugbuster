import { useThemeToken } from '@Common/hooks';
import { Flex, Form, FormItemProps, InputNumber, Skeleton, Typography } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps extends FormItemProps {
    freeCount?: number
    isLoading?: boolean
    initialCountValue?: number
}

export const MaxParallelsInput = ({ freeCount = 0, initialCountValue, style, isLoading, label, ...props }: IProps) => {
    const { t } = useTranslation()
    const [value, setValue] = useState<null | number>(initialCountValue || 0)
    const token = useThemeToken()

    const remaining = freeCount - (value || 0)

    return (
        <Flex style={ style } vertical>
            <Typography.Text style={ { marginBottom: 4 } }>{label}</Typography.Text>
            <Form.Item noStyle { ...props }>
                <InputNumber
                    max={ freeCount }
                    min={ 0 }
                    onChange={ setValue }
                    onKeyDown={ (e) => {
                        if (e.key === '-') {
                            e.preventDefault()

                            return
                        }
                        if (e.key >= '0' && e.key <= '9') {
                            const newValue = parseInt((value?.toString() || '0') + e.key, 10);

                            if (newValue > freeCount) {
                                e.preventDefault();
                            }
                        }
                    } }
                    placeholder={ '0' }
                    style={ { width: '100%' } }
                    type={ 'number' }
                />
            </Form.Item>
            {isLoading
                ? <Skeleton.Input style={ { height: 22, marginTop: 4 } }/>
                :
                <Typography.Text style={ { marginTop: '4px' } }>
                    {t('streams.free_streams')}
                    {' '}
                    <span style={ { color: remaining === 0 ? token.colorErrorText : undefined } }>
                        {remaining > 0 ? remaining : 0}
                    </span>
                </Typography.Text>}
        </Flex>
    )

}

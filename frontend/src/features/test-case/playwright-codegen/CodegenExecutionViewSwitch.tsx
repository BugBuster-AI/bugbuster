import { Flex, Segmented } from 'antd'
import { ReactElement } from 'react'
import { useTranslation } from 'react-i18next'

export type TCodegenExecutionView = 'run' | 'codegen'

interface IProps {
    value: TCodegenExecutionView
    onChange: (v: TCodegenExecutionView) => void
}

export const CodegenExecutionViewSwitch = ({ value, onChange }: IProps): ReactElement => {
    const { t } = useTranslation()

    return (
        <Flex align="center" gap={ 8 } style={ { flexWrap: 'wrap', marginBottom: 12 } }>
            <Segmented<TCodegenExecutionView>
                onChange={ onChange }
                options={ [
                    { label: t('codegen.execution_view_run'), value: 'run' },
                    { label: t('codegen.execution_view_codegen'), value: 'codegen' },
                ] }
                value={ value }
            />
        </Flex>
    )
}

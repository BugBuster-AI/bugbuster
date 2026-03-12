import { useThemeToken } from '@Common/hooks';
import { TCaseExecutionMode, useCreateRunStore } from '@Features/runs/create-run-from-cases/store';
import { Flex, Input, Typography } from 'antd';
import flatMap from 'lodash/flatMap';
import map from 'lodash/map';
import size from 'lodash/size';
import values from 'lodash/values';
import { useTranslation } from 'react-i18next';

interface IProps {
    executionMode: TCaseExecutionMode
}

export const TopToolbar = ({ executionMode }: IProps) => {
    const tempCases = useCreateRunStore((state) => state.tempCases)
    const token = useThemeToken()
    
    const allCases = flatMap(values(tempCases), (cases) =>
        map(cases.filter((c) => c.executionMode === executionMode), 'id')
    )

    const sizeCases = size(allCases)
    const { t } = useTranslation()

    return (
        <Flex align={ 'center' } gap={ 24 } style={ { marginBlock: 16 } }>
            <Input.Search style={ { width: 320 } } />

            {tempCases && (
                <Typography.Text style={ { color: token.colorTextDescription } }>
                    {t('create_run.case_selected', { count: sizeCases })}
                </Typography.Text>
            )}
        </Flex>
    )
}

import { FieldTimeOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ERunStatus } from '@Entities/runs/models';
import { useRunningStore } from '@Pages/RunningCase/store';
import { Flex, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

export const ResultLog = () => {
    const run = useRunningStore((state) => state.currentRun)
    const { t } = useTranslation()
    const token = useThemeToken()

    const status = run?.status

    const getColors = () => {
        switch (status) {
            case ERunStatus.FAILED:
                return {
                    color: token.colorErrorText,
                    border: `1px solid ${token.colorErrorBorder}`,
                    backgroundColor: token.colorErrorBg
                }
            case ERunStatus.PASSED:
                return {
                    color: token.colorSuccess,
                    border: `1px solid ${token.colorSuccessBorder}`,
                    backgroundColor: token.colorSuccessBg
                }
            default:
                return {
                    color: token.colorText,
                    border: `1px solid ${token.colorBorder}`,
                    backgroundColor: token.colorBgLayout
                }
        }

    }

    const { color, backgroundColor, border } = getColors()

    return (
        <Flex
            gap={ 8 }
            justify="space-between"
            style={ {
                backgroundColor,
                border,
                color,
                padding: '16px',
                borderRadius: '8px',
            } }
            vertical
        >
            <Flex gap={ 8 } vertical>
                {Boolean(run?.run_summary) && (
                    <Typography.Text style={ { whiteSpace: 'pre-line', maxHeight: 142, overflow: 'auto' } } >
                        {run?.run_summary}
                    </Typography.Text>
                )}
            </Flex>

            <Flex justify={ 'space-between' } style={ { width: '100%' } }>
                <Typography.Text>{t('running_page.total_time')}</Typography.Text>
                <Typography.Text>
                    <FieldTimeOutlined style={ { marginRight: '8px' } }/>

                    {formatSeconds(Number(run?.complete_time || 0), t)}
                </Typography.Text>
            </Flex>
        </Flex>
    )
}

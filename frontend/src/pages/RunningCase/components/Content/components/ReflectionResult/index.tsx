import { StatusIndicator } from '@Common/components';
import { useThemeToken } from '@Common/hooks';
import { ERunStatus, IReflectionResult } from '@Entities/runs/models';
import { getReflectionStatus } from '@Entities/runs/utils/getReflectionStatus.ts';
import { Flex, Typography } from 'antd';


interface IProps extends IReflectionResult {
    status?: ERunStatus
}

export const ReflectionResult = ({ 
    reflection_title, 
    reflection_result, 
    reflection_description 
}: IProps) => {
    const token = useThemeToken()

    const getColor = (reflection_result: ERunStatus | boolean) => {

        if (reflection_result === false || reflection_result === ERunStatus.FAILED) {

            return {
                border: token.colorErrorBorder,
                background: token.colorErrorBg
            }
        }

        if (reflection_result === true || reflection_result === ERunStatus.PASSED) {
            return {
                border: token.colorSuccessBorder,
                background: token.colorSuccessBg
            }
        }

        return {
            border: token.colorBorder,
            background: token.colorBgBase
        }
    }

    const colors = getColor(reflection_result)

    return (
        <Flex gap={ 8 } style={ { width: '100%', marginBottom: 16 } } vertical>
            <Flex
                align={ 'flex-start' }
                gap={ 16 }
                style={ {
                    width: '100%',
                    border: `1px solid ${colors.border}`,
                    borderRadius: '6px',
                    padding: '20px 24px',
                    backgroundColor: colors.background,
                    whiteSpace: 'pre-line',
                    overflow: 'auto',
                    maxHeight: 142,
                } }
            >
                <StatusIndicator status={ getReflectionStatus(reflection_result) }/>
                <Flex gap={ 4 } vertical>
                    {Boolean(reflection_title) && <Typography.Text>{reflection_title}</Typography.Text>}
                    {Boolean(reflection_description) && <Typography.Text>{reflection_description}</Typography.Text>}
                </Flex>
            </Flex>

        </Flex>
    )
}

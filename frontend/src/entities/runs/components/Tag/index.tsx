import { useThemeToken } from '@Common/hooks';
import { ERunStatus } from '@Entities/runs/models';
import { Tag } from 'antd';
import { ReactElement } from 'react';

interface IProps {
    status: ERunStatus
}

export const TableTag = ({ status }: IProps): ReactElement => {
    const token = useThemeToken()

    const getProps = () => {
        switch(status) {
            case ERunStatus.IN_PROGRESS:
                return {
                    backgroundColor: token.geekblue1,
                    color: token.geekblue6,
                    borderColor: token.geekblue3
                }
            case ERunStatus.FAILED:
                return {
                    backgroundColor: token.red1,
                    color: token.red6,
                    borderColor: token.red3
                }
            case ERunStatus.PASSED:
                return {
                    color: token.green6,
                    backgroundColor: token.green1,
                    borderColor: token.green3

                }
            default: return {
                backgroundColor: token.colorFillQuaternary,
                borderColor: token.colorBorder,
                color: token.colorText,

            }
        }
    }

    return <Tag style={ { ...getProps() } }>{status}</Tag>
}

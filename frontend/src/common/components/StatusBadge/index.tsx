import { getStatusColors as getColor } from '@Common/utils';
import { ERunStatus } from '@Entities/runs/models';
import { Tag } from 'antd';
import upperFirst from 'lodash/upperFirst';
import { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    status?: ERunStatus;
    label?: string
    onClick?: () => void
    inverted?: boolean
    style?: CSSProperties
}

const getStatusColor = (status: ERunStatus): { color: string, text?: string } => {
    const color = getColor(status)

    switch (status) {
        case ERunStatus.IN_PROGRESS:
        case ERunStatus.PASSED:
        case ERunStatus.FAILED:
        case ERunStatus.UNTESTED:
        case ERunStatus.SCHEDULED:
        case ERunStatus.BLOCKED:
        case ERunStatus.SKIPPED:
        case ERunStatus.STOPPED:
        case ERunStatus.IN_QUEUE:
        case ERunStatus.INVALID:
        case ERunStatus.RETEST:
        case ERunStatus.STOP_IN_PROGRESS:
        case ERunStatus.AFTER_STEP_FAILURE:
            return {
                color
            }
        default:
            return {
                color,
                text: upperFirst(status)
            };
    }
};

export const StatusBadge = ({ status = ERunStatus.UNTESTED, inverted, label, onClick, style }: IProps) => {
    const { t } = useTranslation()
    const { color, text } = getStatusColor(status) || {};

    const clickableStyles: CSSProperties = onClick ? {
        cursor: 'pointer'
    } : {}

    const withInverted = inverted ? `${color}-inverse` : color
    const invertedDefaultColor = color === 'default' && inverted ? {
        color: 'black',
        border: '1px solid black',
    } : {}

    return (
        <Tag
            color={ withInverted }
            onClick={ onClick }
            style={ { ...invertedDefaultColor, paddingBlock: 1, ...clickableStyles, ...style } }
        >
            {label || text || t(`statuses.${status}`)}
        </Tag>
    );
};

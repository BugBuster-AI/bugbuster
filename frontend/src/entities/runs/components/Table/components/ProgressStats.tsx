import { getStatusColors } from '@Common/utils';
import { ERunStatus, IRunStats } from '@Entities/runs/models';
import { Tag, Flex, Tooltip } from 'antd';
import map from 'lodash/map';
import values from 'lodash/values';
import { ComponentProps, CSSProperties, ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

interface IProgressProps {
    total?: number;
    stats: IRunStats
    style?: CSSProperties
    variant?: 'default' | 'mini'
}

const getColor = (key: keyof IRunStats): ComponentProps<typeof Tag>['color'] => {
    const color = getStatusColors(key as ERunStatus)

    if (color === 'default') {
        return color
    }

    return `${color}-inverse`
}

export const ProgressStats = ({ total, stats, style, variant = 'default' }: IProgressProps): ReactElement => {
    const totalStat = values(stats).reduce((acc, value) => acc + value, 0)
    const { t } = useTranslation()
    const isMini = variant === 'mini'

    const componentStyles: CSSProperties = isMini ? {
        height: '8px',
        borderRadius: '4px'
    } : {}

    return (
        <Flex style={ { ...style, ...componentStyles } }>
            {map(Object.entries(stats), ([key, value]) => {
                const percentage = (value / (total || totalStat)) * 100;
                const color = getColor(key as keyof IRunStats)

                if (value === 0) {
                    return null
                }

                const tooltipTitle = `${value} ${t(`statuses.${key}`)}`

                return (
                    <Tooltip
                        key={ `progressBar-${key}` }
                        title={ tooltipTitle }>
                        <Tag
                            className={ 'runs-progress-bar' }
                            color={ color }
                            style={ {
                                textAlign: 'center',
                                margin: 0,
                                paddingInline: 0,
                                width: `${percentage}%`
                            } }
                        >
                            {!isMini && value}
                        </Tag>
                    </Tooltip>
                )
            }
            )}
        </Flex>

    );
};

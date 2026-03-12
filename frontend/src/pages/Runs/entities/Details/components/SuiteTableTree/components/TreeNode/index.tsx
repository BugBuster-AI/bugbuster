import { TextWithIcon } from '@Common/components';
import { formatSeconds } from '@Common/utils/formatSeconds.ts';
import { ProgressStats } from '@Entities/runs/components/Table/components';
import { IRunStats } from '@Entities/runs/models';
import { Flex, Typography } from 'antd';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';

interface INodeHeaderProps {
    name: string
    complete_time?: string | null
    stats?: IRunStats
    onClick?: () => void
}

export const NodeHeader = memo(({ name, stats, complete_time, onClick }: INodeHeaderProps) => {
    const { t } = useTranslation()

    return (
        <Flex
            justify={ 'space-between' }
            onClick={ (e) => {
                e.stopPropagation()
                onClick && onClick()
            } }>
            <Typography.Title level={ 5 }>{name}</Typography.Title>

            <Flex align={ 'center' } gap={ 40 }>
                {complete_time && <TextWithIcon>{formatSeconds(Number(complete_time || 0), t)}</TextWithIcon>}
                {stats && <ProgressStats
                    stats={ stats }
                    style={ { width: 300 } }
                    variant="mini"
                />}
            </Flex>
        </Flex>
    )
})

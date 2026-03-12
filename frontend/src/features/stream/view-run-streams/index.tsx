import { getLimits } from '@Common/utils/getLimits.ts';
import { IStreamStat } from '@Entities/stream/models';
import { useStreamStore } from '@Entities/stream/store';
import { StreamController } from '@Features/stream/stream-controller';
import { Flex, Skeleton, Typography } from 'antd';
import get from 'lodash/get';
import { ReactElement, useEffect } from 'react';
import { useTranslation } from 'react-i18next';

interface IProps {
    groupRunId?: string
    onLoad?: (data: IStreamStat | null) => void
}

export const ViewRunStreams = ({ groupRunId, onLoad }: IProps): ReactElement => {
    const loading = useStreamStore((state) => state.loading)
    const error = useStreamStore((state) => state.error)
    const streams = useStreamStore((state) => state.streams)
    const { t } = useTranslation()

    const currentRunStreams = groupRunId ? get(streams?.group_run_statistics, (groupRunId), null) : null

    const { title } = getLimits({
        limitValue: currentRunStreams?.total_streams,
        remaining: currentRunStreams?.active_streams
    })

    useEffect(() => {
        onLoad?.(currentRunStreams)
    }, [currentRunStreams]);

    const View = () => (
        (currentRunStreams && title)
            ? <Flex>
                <Typography.Text>
                    {t('streams.run', { info: title })}
                </Typography.Text>
            </Flex>
            : null
    )


    return (
        <StreamController>
            {!error &&
                (loading
                    ? <Skeleton.Input/>
                    : <View/>
                )
            }
        </StreamController>
    )
}

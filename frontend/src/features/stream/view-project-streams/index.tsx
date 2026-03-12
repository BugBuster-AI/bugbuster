import { NodeExpandOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { getLimits } from '@Common/utils/getLimits.ts';
import { useProjectStore } from '@Entities/project/store';
import { useStreamStore } from '@Entities/stream/store';
import { StreamController } from '@Features/stream/stream-controller';
import { Flex, Skeleton, Typography } from 'antd';
import { ReactElement } from 'react';
import { useTranslation } from 'react-i18next';

export const ViewProjectStreams = (): ReactElement => {
    const currentProjectStreams = useStreamStore((state) => state.currentProjectStreams)
    const loading = useStreamStore((state) => state.loading)
    const error = useStreamStore((state) => state.error)
    const project = useProjectStore((state) => state.currentProject)
    const { t } = useTranslation()
    const token = useThemeToken()

    const { title } = getLimits({
        limitValue: currentProjectStreams?.total_streams,
        remaining: currentProjectStreams?.active_streams
    })

    const View = () => (
        (currentProjectStreams && title) ? <Flex
            align={ 'center' }
            gap={ 16 }
            justify={ 'space-between' }
        >
            <Typography.Text style={ { color: token.colorTextSecondary } }>
                {t('streams.projectOnly')}
            </Typography.Text>
            <Typography.Text style={ { color: token.colorTextSecondary } }>
                <NodeExpandOutlined
                    style={ { fontSize: 16, color: token.colorTextSecondary, paddingRight: 8 } }
                />
                {title}
            </Typography.Text>
        </Flex>
            : null
    )


    return (
        <StreamController projectId={ project?.project_id }>
            {!error &&
                (loading
                    ? <Skeleton.Input/>
                    : <View/>
                )
            }
        </StreamController>
    )
}

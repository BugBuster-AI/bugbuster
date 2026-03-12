import { NodeExpandOutlined } from '@ant-design/icons';
import { useThemeToken } from '@Common/hooks';
import { getLimits } from '@Common/utils/getLimits.ts';
import { useStreamStore } from '@Entities/stream/store';
import { StreamController } from '@Features/stream/stream-controller';
import { Flex, Skeleton, Typography } from 'antd';
import { useTranslation } from 'react-i18next';

export const ViewWorkspaceStreams = () => {
    const streams = useStreamStore((state) => state.streams)
    const loading = useStreamStore((state) => state.loading)
    const error = useStreamStore((state) => state.error)
    const { t } = useTranslation()
    const workspaceStreams = streams?.workspace_statistics
    const token = useThemeToken()

    const { title } = getLimits({
        limitValue: workspaceStreams?.total_streams,
        remaining: workspaceStreams?.active_streams
    })

    const View = () => (
        (workspaceStreams && !!title) ? (
            <Flex
                align={ 'center' }
                gap={ 16 }
                style={ { borderRadius: 8, background: token.colorFillTertiary, padding: 8 } }
            >
                <Typography.Text>
                    {t('streams.workspaceOnly')}
                </Typography.Text>
                <Typography.Text style={ { color: token.colorTextSecondary } }>
                    <NodeExpandOutlined
                        style={ { fontSize: 16, color: token.colorTextSecondary, paddingRight: 8 } }
                    />
                    {title}
                </Typography.Text>
            </Flex>
        )
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

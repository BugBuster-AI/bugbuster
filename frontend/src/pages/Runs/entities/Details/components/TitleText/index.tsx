import { StatusBadge } from '@Common/components';
import { ViewRunStreams } from '@Features/stream/view-run-streams';
import { useGroupedRunStore } from '@Pages/Runs/entities/Details/store';
import { Flex, Skeleton, Typography } from 'antd';

interface IProps {
    loading: boolean
}

export const TitleText = ({ loading }: IProps) => {
    const item = useGroupedRunStore((state) => state.runItem)
    const setStreams = useGroupedRunStore((state) => state.setStreams)

    return (
        <Flex align="center" flex={ 1 } gap={ 8 }>
            <Skeleton loading={ loading && !item } paragraph={ { rows: 0 } } title={ { width: 90 } }>
                <Flex vertical>
                    <Flex align={ 'center' } gap={ 8 }>
                        <Typography.Title level={ 4 } style={ { margin: 0, whiteSpace: 'nowrap' } }>
                            {item?.name}
                        </Typography.Title>
                        <StatusBadge status={ item?.status }/>
                    </Flex>
                    <ViewRunStreams groupRunId={ item?.group_run_id } onLoad={ setStreams }/>
                </Flex>
            </Skeleton>
        </Flex>
    )
}

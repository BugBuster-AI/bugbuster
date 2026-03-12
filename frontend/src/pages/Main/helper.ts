import { IProjectListItem } from '@Entities/project';
import { ITableProjectListItem } from '@Entities/project/components/Table';
import { IStreamsStatList } from '@Entities/stream/models';
import get from 'lodash/get';
import map from 'lodash/map';

interface IProps {
    projects?: IProjectListItem[]
    streams?: IStreamsStatList['project_statistics']
}

export const adaptProjectsData = ({ projects, streams }: IProps): ITableProjectListItem[] => {

    return map(projects, (item) => {
        const streamsData = get(streams, item.project_id, null)
        const streamsTitle = streamsData ? `${streamsData?.active_streams}/${streamsData?.total_streams}` : '-'

        return {
            max_streams: streams ? streamsTitle : '',
            ...item
        } as ITableProjectListItem
    })

}

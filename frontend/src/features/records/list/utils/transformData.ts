import { IShortenedListItem } from '@Entities/records/components/ShortenedTable';
import { IHappyPassListItem, IRecordListItem } from '@Entities/records/models';
import map from 'lodash/map';

export const transformData = (data?: IHappyPassListItem[]): IShortenedListItem[] => {
    if (!data) return []

    return map(data, (item) => ({
        name: item.name,
        context: item.context,
        date: item.created_at,
        id: item.happy_pass_id
    }))
}

export const transformLongData = (data?: IHappyPassListItem[]): IRecordListItem[] => {
    if (!data) return []

    return map(data, (item) => ({
        name: item.name,
        id: item.happy_pass_id,
        date: item.created_at,
        context: item.context,
        createdBy: 'Created by'
    }))
}

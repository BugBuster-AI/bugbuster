import { ISuite } from '@Entities/suite/models';
import type { TreeDataNode } from 'antd';

export interface ITreeListItem extends TreeDataNode {
    count?: number
    parent_suite?: ITreeListItem | null
    suite: ISuite
    selfCount?: number
}

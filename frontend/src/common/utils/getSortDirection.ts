import { SortOrder } from 'antd/es/table/interface';

export const getSortDirection = (dir?: SortOrder): 'asc' | 'desc' | undefined => {
    if (!dir) return undefined
    switch (dir) {
        case 'ascend':
            return 'asc'
        case'descend':
            return 'desc'
    }
}

import { SharedStepsApi } from '@Entities/shared-steps/api';
import {
    IGetSharedStepByIdRequest,
    IGetSharedStepsListByNameRequest,
    IGetSharedStepsListRequest
} from '@Entities/shared-steps/models';
import { sharedStepsKeys } from '@Entities/shared-steps/queries/query-keys';
import { queryOptions } from '@tanstack/react-query';
import trim from 'lodash/trim';

const sharedStepsApi = SharedStepsApi.getInstance()

const getListParams = (params: IGetSharedStepsListRequest) => {
    if (trim(params.search) === '') {
        delete params.search
    }

    return params
}

export const sharedStepsQueries = {
    all: () => [sharedStepsKeys.index],

    list: (params: IGetSharedStepsListRequest) => queryOptions({
        queryKey: [...sharedStepsQueries.all(), sharedStepsKeys.list, getListParams(params)],
        queryFn: () => sharedStepsApi.getList(getListParams(params)),
        enabled: !!params.project_id
    }),

    byId: (params: IGetSharedStepByIdRequest, enabled = true) => queryOptions({
        queryKey: [...sharedStepsQueries.all(), sharedStepsKeys.detail, params],
        queryFn: () => sharedStepsApi.getById(params),
        enabled
    }),

    listByName: (params: IGetSharedStepsListByNameRequest) => queryOptions({
        queryKey: [...sharedStepsQueries.all(), sharedStepsKeys.listByName, params],
        queryFn: () => sharedStepsApi.getListByName(params)
    })
}

export * from './query-keys'

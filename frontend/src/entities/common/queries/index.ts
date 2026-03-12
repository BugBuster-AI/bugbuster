import { CommonApi } from '@Entities/common/api';
import { GetFlagCatalogResponseDto, IGetFlagUserResponseDto } from '@Entities/common/models/get-flag.dto.ts';
import { QueryObserverOptions, queryOptions } from '@tanstack/react-query';

const commonApi = CommonApi.getInstance()

export const commonQueries = {
    flagCatalog: (userId?: string, options?: Partial<QueryObserverOptions<GetFlagCatalogResponseDto, Error>>) =>
        queryOptions({
            queryKey: ['flags', 'catalog', userId],
            queryFn: () => commonApi.getFlagsCatalog(),
            ...options
        }),


    userFlags: (userId?: string, options?: Partial<QueryObserverOptions<IGetFlagUserResponseDto, Error>>) =>
        queryOptions({
            queryKey: ['flags', 'user', userId],
            queryFn: () => commonApi.getUserFlags(),
            ...options
        }),

}

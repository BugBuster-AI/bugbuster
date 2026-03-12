import { CommonApi } from '@Entities/common/api';
import { IGetCoordinatesRequest } from '@Entities/common/models/get-coordinates.ts';
import { IUpdateFlagRequestDto } from '@Entities/common/models/get-flag.dto.ts';
import { IGetReflectionRequest } from '@Entities/common/models/get-reflection.ts';
import { commonQueries } from '@Entities/common/queries/index.ts';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ICreateContextScreenshotDtoRequest, IDeleteContextScreenshotDtoRequest } from '../models/context-screenshot';
import { IDescribeElementRequestDto } from '../models/describe-element';

const commonApi = CommonApi.getInstance()

export const useUpdateFlag = () => {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (data: IUpdateFlagRequestDto) => commonApi.updateFlag(data),
        onSuccess: (data) => {
            queryClient.invalidateQueries(commonQueries.userFlags(data.user_id));
        }
    })
}

type WithSignal<T> = T & {
    signal?: AbortSignal
}

export const useGetCoordinates = () => {
    // const queryClient = useQueryClient()

    return useMutation({
        mutationFn: ({ signal, ...data }: WithSignal<IGetCoordinatesRequest>) => commonApi.getCoordinates(data, signal),
    })
}

export const useGetReflection = () => {
    return useMutation({
        mutationFn: ({ signal, ...data }: WithSignal<IGetReflectionRequest>) => commonApi.getReflection(data, signal),
    })
}

export const useDescribeElement = () => {
    return useMutation({
        mutationFn: (data: IDescribeElementRequestDto) => commonApi.describeElement(data),
    })
}

export const useCreateContextScreenshot = () => {
    return useMutation({
        mutationFn: ({ signal, ...data }: WithSignal<ICreateContextScreenshotDtoRequest>) => 
            commonApi.createContextScreenshot(data, signal),
    })
}

export const useDeleteContextScreenshot = () => {
    return useMutation({
        mutationFn: ({ signal, ...data }: WithSignal<IDeleteContextScreenshotDtoRequest>) =>
            commonApi.deleteContextScreenshot(data, signal),
    })
}

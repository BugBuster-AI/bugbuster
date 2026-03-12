import { $api } from '@Common/api';
import { IGetCoordinatesRequest, IGetCoordinatesResponse } from '@Entities/common/models/get-coordinates.ts';
import {
    GetFlagCatalogResponseDto,
    IGetFlagUserResponseDto,
    IUpdateFlagRequestDto
} from '@Entities/common/models/get-flag.dto.ts';
import { IGetReflectionRequest, IGetReflectionResponse } from '@Entities/common/models/get-reflection.ts';
import { 
    ICreateContextScreenshotDtoRequest, 
    ICreateContextScreenshotDtoResponse, 
    IDeleteContextScreenshotDtoRequest, 
    IDeleteContextScreenshotDtoResponse 
} from '../models/context-screenshot';
import { IDescribeElementRequestDto, IDescribeElementResponseDto } from '../models/describe-element';

export class CommonApi {
    private static instance: CommonApi | null

    public static getInstance (): CommonApi {
        if (!this.instance) {
            this.instance = new CommonApi()

            return this.instance
        }

        return this.instance
    }

    async getFlagsCatalog (): Promise<GetFlagCatalogResponseDto> {
        return (await $api.get(`flags/catalog`)).data
    }

    async getUserFlags (): Promise<IGetFlagUserResponseDto> {
        return (await $api.get(`flags/get_user_flags`)).data
    }

    async updateFlag ({ flag_name, ...data }: IUpdateFlagRequestDto): Promise<IGetFlagUserResponseDto> {
        return (await $api.put(`flags/${flag_name}`, data)).data
    }

    async getCoordinates (data: IGetCoordinatesRequest, signal?: AbortSignal): Promise<IGetCoordinatesResponse> {
        return (await $api.post(`tools/get_coordinates`, data, { signal })).data
    }

    async getReflection (data: IGetReflectionRequest, signal?: AbortSignal): Promise<IGetReflectionResponse> {
        return (await $api.post(`tools/get_reflection`, data, { signal, timeout: 90000 })).data
    }

    async describeElement (data: IDescribeElementRequestDto): Promise<IDescribeElementResponseDto> {
        return (await $api.post(`tools/describe_element`, data)).data
    }

    async createContextScreenshot (data: ICreateContextScreenshotDtoRequest, signal?: AbortSignal):
     Promise<ICreateContextScreenshotDtoResponse> {
        return (await $api.post(`tools/create_context_screenshot`, data, { signal })).data
    }

    async deleteContextScreenshot (data: IDeleteContextScreenshotDtoRequest, signal?: AbortSignal):
     Promise<IDeleteContextScreenshotDtoResponse> {
        return (await $api.delete(`tools/delete_context_screenshot`, { data, signal })).data
    }
}

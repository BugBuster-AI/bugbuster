import { IMedia } from '@Entities/runs/models';

export interface ICreateContextScreenshotDtoRequest {
    image_base64_string: string;
    minio_path?: Record<string, string>
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

export interface ICreateContextScreenshotDtoResponse extends IMedia {}
export interface IDeleteContextScreenshotDtoRequest {
    minio_path: IMedia
}

export interface IDeleteContextScreenshotDtoResponse {}

import { IMedia } from '@Entities/runs/models'

export interface IGetCoordinatesRequest {
    image_base64_string?: string
    prompt?: string
    minio_path?: {
        bucket: string
        file: string
    }
    context_screenshot_path?: IMedia
}

export interface IGetCoordinatesResponse {
    result_id: string;
    generate_time: string;
    original_prompt: string;
    final_prompt: string;
    coords: number[]
    original_image_base64: string;
    annotated_image_base64: string
}

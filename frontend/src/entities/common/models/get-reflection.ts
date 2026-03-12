import { IMedia } from '@Entities/runs/models'

export interface IGetReflectionRequest {
    reflection_instruction?: string
    before_image_base64_string?: string
    before_minio_path?: IMedia
    after_image_base64_string?: string
    after_minio_path?: IMedia
    use_single_screenshot?: boolean
}

export interface IGetReflectionResponse {
    result_id: string;
    reflection_time: string;
    reflection_step: string;
    reflection_title: string;
    reflection_description: string;
    reflection_thoughts: string;
    reflection_result: 'passed' | 'failed' | boolean;
}

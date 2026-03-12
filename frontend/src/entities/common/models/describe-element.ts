export interface IDescribeElementRequestDto {
    image_base64_string: string;
    minio_path?: Record<string, string>
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    thinking_mode: boolean;
}

export interface IDescribeElementResponseDto {
    generate_time: string;
    bounding_box: {
        x1: number;
        y1: number;
        x2: number;
        y2: number;
    };
    description: string;
    original_image_base64: string;
    result_id: string
}
